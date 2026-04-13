/**
 * FieldStorage — Almacenamiento robusto para trabajo de campo sin señal
 * Usa IndexedDB para almacenar 100+ MB de datos (fotos, nodos, proyectos)
 * Diseñado para cartógrafos en zonas veredales sin cobertura durante días
 */
const FieldStorage = {
    DB_NAME: 'campo_lite_db',
    DB_VERSION: 2,
    db: null,

    // ============================================================
    // INIT
    // ============================================================
    async init() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(this.DB_NAME, this.DB_VERSION);

            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                // Proyectos/levantamientos
                if (!db.objectStoreNames.contains('projects')) {
                    const projStore = db.createObjectStore('projects', { keyPath: 'id' });
                    projStore.createIndex('timestamp', 'timestamp');
                    projStore.createIndex('synced', 'synced');
                }
                // Nodos GPS
                if (!db.objectStoreNames.contains('nodes')) {
                    const nodeStore = db.createObjectStore('nodes', { keyPath: 'id' });
                    nodeStore.createIndex('projectId', 'projectId');
                }
                // Fotos (blobs grandes)
                if (!db.objectStoreNames.contains('photos')) {
                    const photoStore = db.createObjectStore('photos', { keyPath: 'id' });
                    photoStore.createIndex('projectId', 'projectId');
                    photoStore.createIndex('nodeId', 'nodeId');
                }
                // Cola de sincronización
                if (!db.objectStoreNames.contains('syncQueue')) {
                    db.createObjectStore('syncQueue', { keyPath: 'id' });
                }
            };

            req.onsuccess = (e) => {
                this.db = e.target.result;
                console.log('[FieldStorage] IndexedDB ready');
                resolve();
            };

            req.onerror = (e) => {
                console.error('[FieldStorage] IndexedDB failed:', e.target.error);
                reject(e.target.error);
            };
        });
    },

    // ============================================================
    // GENERIC CRUD
    // ============================================================
    _tx(storeName, mode = 'readonly') {
        return this.db.transaction(storeName, mode).objectStore(storeName);
    },

    async put(storeName, data) {
        return new Promise((resolve, reject) => {
            const req = this._tx(storeName, 'readwrite').put(data);
            req.onsuccess = () => resolve(data);
            req.onerror = (e) => reject(e.target.error);
        });
    },

    async get(storeName, id) {
        return new Promise((resolve, reject) => {
            const req = this._tx(storeName).get(id);
            req.onsuccess = () => resolve(req.result);
            req.onerror = (e) => reject(e.target.error);
        });
    },

    async getAll(storeName) {
        return new Promise((resolve, reject) => {
            const req = this._tx(storeName).getAll();
            req.onsuccess = () => resolve(req.result || []);
            req.onerror = (e) => reject(e.target.error);
        });
    },

    async getAllByIndex(storeName, indexName, value) {
        return new Promise((resolve, reject) => {
            const store = this._tx(storeName);
            const index = store.index(indexName);
            const req = index.getAll(value);
            req.onsuccess = () => resolve(req.result || []);
            req.onerror = (e) => reject(e.target.error);
        });
    },

    async delete(storeName, id) {
        return new Promise((resolve, reject) => {
            const req = this._tx(storeName, 'readwrite').delete(id);
            req.onsuccess = () => resolve();
            req.onerror = (e) => reject(e.target.error);
        });
    },

    // ============================================================
    // PROJECT MANAGEMENT
    // ============================================================
    async saveProject(project) {
        project.id = project.id || 'proj_' + Date.now();
        project.timestamp = project.timestamp || new Date().toISOString();
        project.synced = false;
        return this.put('projects', project);
    },

    async getProjects() {
        return this.getAll('projects');
    },

    // ============================================================
    // NODES
    // ============================================================
    async saveNode(node) {
        node.id = node.id || 'node_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
        return this.put('nodes', node);
    },

    async getNodesByProject(projectId) {
        return this.getAllByIndex('nodes', 'projectId', projectId);
    },

    async deleteNode(nodeId) {
        // Also delete associated photos
        const photos = await this.getAllByIndex('photos', 'nodeId', nodeId);
        for (const p of photos) {
            await this.delete('photos', p.id);
        }
        return this.delete('nodes', nodeId);
    },

    // ============================================================
    // PHOTOS (stored as Blob, not base64 — much more efficient)
    // ============================================================
    async savePhoto(photoData) {
        photoData.id = photoData.id || 'photo_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
        return this.put('photos', photoData);
    },

    async getPhotosByProject(projectId) {
        return this.getAllByIndex('photos', 'projectId', projectId);
    },

    async getPhotosByNode(nodeId) {
        return this.getAllByIndex('photos', 'nodeId', nodeId);
    },

    // ============================================================
    // STORAGE INFO
    // ============================================================
    async getStorageInfo() {
        if (navigator.storage && navigator.storage.estimate) {
            const est = await navigator.storage.estimate();
            return {
                used: est.usage || 0,
                quota: est.quota || 0,
                percent: est.quota ? Math.round((est.usage / est.quota) * 100) : 0,
                usedMB: Math.round((est.usage || 0) / 1024 / 1024),
                quotaMB: Math.round((est.quota || 0) / 1024 / 1024)
            };
        }
        return { used: 0, quota: 0, percent: 0, usedMB: 0, quotaMB: 0 };
    },

    // ============================================================
    // EXPORT — GeoJSON (ArcGIS compatible)
    // ============================================================
    nodesToGeoJSON(nodesArray, projectName) {
        return {
            type: 'FeatureCollection',
            name: projectName || 'campo_lite_export',
            crs: {
                type: 'name',
                properties: { name: 'urn:ogc:def:crs:EPSG::4326' }
            },
            features: nodesArray.map((n, idx) => ({
                type: 'Feature',
                properties: {
                    id: idx + 1,
                    seq: n.seq || idx + 1,
                    potential_clients: n.clients || 0,
                    gas_points: n.gas || 0,
                    condition: n.condition || 'normal',
                    has_water_source: n.condition === 'water',
                    is_rocky_ground: n.condition === 'rocky',
                    observations: n.obs || '',
                    latitude: n.lat,
                    longitude: n.lng,
                    timestamp: n.timestamp || new Date().toISOString()
                },
                geometry: {
                    type: 'Point',
                    coordinates: [n.lng, n.lat]
                }
            })),
            // Add linestring feature for the route
            ...(nodesArray.length > 1 ? {
                features: [
                    ...nodesArray.map((n, idx) => ({
                        type: 'Feature',
                        properties: {
                            id: idx + 1,
                            seq: n.seq || idx + 1,
                            potential_clients: n.clients || 0,
                            gas_points: n.gas || 0,
                            condition: n.condition || 'normal',
                            has_water_source: n.condition === 'water',
                            is_rocky_ground: n.condition === 'rocky',
                            observations: n.obs || '',
                            latitude: n.lat,
                            longitude: n.lng
                        },
                        geometry: { type: 'Point', coordinates: [n.lng, n.lat] }
                    })),
                    {
                        type: 'Feature',
                        properties: { name: projectName + '_trazado', type: 'route', total_nodes: nodesArray.length },
                        geometry: {
                            type: 'LineString',
                            coordinates: nodesArray.map(n => [n.lng, n.lat])
                        }
                    }
                ]
            } : {})
        };
    },

    // ============================================================
    // EXPORT — CSV (ArcGIS XY Table import)
    // ============================================================
    nodesToCSV(nodesArray, projectName) {
        const header = 'ID,Secuencia,Latitud,Longitud,Clientes_Potenciales,Puntos_Gas,Condicion_Terreno,Afectacion_Hidrica,Terreno_Rocoso,Observaciones,Proyecto,Fecha\n';
        const rows = nodesArray.map((n, idx) =>
            [
                idx + 1,
                n.seq || idx + 1,
                n.lat.toFixed(8),
                n.lng.toFixed(8),
                n.clients || 0,
                n.gas || 0,
                n.condition || 'normal',
                n.condition === 'water' ? 'SI' : 'NO',
                n.condition === 'rocky' ? 'SI' : 'NO',
                '"' + (n.obs || '').replace(/"/g, '""') + '"',
                '"' + (projectName || '') + '"',
                n.timestamp || new Date().toISOString()
            ].join(',')
        ).join('\n');
        return header + rows;
    },

    // ============================================================
    // EXPORT — GPX (GPS Exchange Format)
    // ============================================================
    nodesToGPX(nodesArray, projectName) {
        const now = new Date().toISOString();
        const wpts = nodesArray.map(n => `
  <wpt lat="${n.lat}" lon="${n.lng}">
    <name>Nodo ${n.seq || ''}</name>
    <desc>Clientes: ${n.clients || 0}, Gas: ${n.gas || 0}, Condicion: ${n.condition || 'normal'}${n.obs ? ', Obs: ' + n.obs : ''}</desc>
    <time>${n.timestamp || now}</time>
    <extensions>
      <potential_clients>${n.clients || 0}</potential_clients>
      <gas_points>${n.gas || 0}</gas_points>
      <condition>${n.condition || 'normal'}</condition>
    </extensions>
  </wpt>`).join('');

        const trk = nodesArray.length > 1 ? `
  <trk>
    <name>${projectName || 'Trazado'}</name>
    <trkseg>
      ${nodesArray.map(n => `<trkpt lat="${n.lat}" lon="${n.lng}"><time>${n.timestamp || now}</time></trkpt>`).join('\n      ')}
    </trkseg>
  </trk>` : '';

        return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="CampoLite-GestorCartografico"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <metadata>
    <name>${projectName || 'Campo Lite Export'}</name>
    <time>${now}</time>
  </metadata>${wpts}${trk}
</gpx>`;
    },

    // ============================================================
    // EXPORT — Full backup ZIP (nodes + photos + all formats)
    // ============================================================
    async exportFullBackup(nodesArray, photosArray, projectName) {
        if (typeof JSZip === 'undefined') {
            throw new Error('JSZip no cargado');
        }

        const zip = new JSZip();
        const safeName = (projectName || 'campo_lite').replace(/[^a-zA-Z0-9_-]/g, '_');

        // GeoJSON
        zip.file(`${safeName}.geojson`, JSON.stringify(this.nodesToGeoJSON(nodesArray, projectName), null, 2));

        // CSV
        zip.file(`${safeName}.csv`, this.nodesToCSV(nodesArray, projectName));

        // GPX
        zip.file(`${safeName}.gpx`, this.nodesToGPX(nodesArray, projectName));

        // KML
        if (typeof buildKML === 'function') {
            zip.file(`${safeName}.kml`, buildKML(projectName));
        }

        // Raw JSON (complete data for re-import)
        zip.file(`${safeName}_raw.json`, JSON.stringify({
            project: projectName,
            exported: new Date().toISOString(),
            nodes: nodesArray,
            photos_count: photosArray.length,
            system: 'GestorCartografico-CampoLite'
        }, null, 2));

        // Photos folder
        if (photosArray.length > 0) {
            const photosFolder = zip.folder('fotos');
            for (let i = 0; i < photosArray.length; i++) {
                const p = photosArray[i];
                if (p.dataUrl) {
                    // Convert base64 to binary
                    const base64 = p.dataUrl.split(',')[1];
                    photosFolder.file(
                        `foto_${i + 1}_${p.lat ? p.lat.toFixed(4) : 'sin_gps'}_${p.lng ? p.lng.toFixed(4) : ''}.jpg`,
                        base64,
                        { base64: true }
                    );
                } else if (p.blob) {
                    photosFolder.file(`foto_${i + 1}.jpg`, p.blob);
                }
            }
        }

        return zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
    },

    // ============================================================
    // DOWNLOAD HELPER
    // ============================================================
    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    },

    downloadText(text, filename, mimeType) {
        const blob = new Blob([text], { type: mimeType || 'text/plain' });
        this.downloadBlob(blob, filename);
    }
};

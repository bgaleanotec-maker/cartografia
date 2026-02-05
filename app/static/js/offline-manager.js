/* Offline Manager for Gestor Cartográfico */
const OfflineManager = {
    PROJECTS_KEY: 'offline_visits_queue',
    
    init() {
        window.addEventListener('online', this.handleConnectionChange.bind(this));
        window.addEventListener('offline', this.handleConnectionChange.bind(this));
        
        // Initial check
        this.updateIndicator();
        this.syncPendingItems();
    },
    
    handleConnectionChange() {
        this.updateIndicator();
        if (navigator.onLine) {
            this.syncPendingItems();
        }
    },
    
    updateIndicator() {
        const indicator = document.getElementById('connection-status');
        if (!indicator) return;
        
        const isOnline = navigator.onLine;
        indicator.className = isOnline 
            ? 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-full shadow-lg text-sm font-bold flex items-center gap-2 transition-all duration-300'
            : 'fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-full shadow-lg text-sm font-bold flex items-center gap-2 transition-all duration-300';
            
        indicator.innerHTML = isOnline 
            ? '<i class="fas fa-wifi"></i> Online' 
            : '<i class="fas fa-wifi-slash"></i> Offline Mode';
    },
    
    saveVisit(visitData) {
        // Generate a temporary ID
        visitData.local_id = 'visit_' + Date.now();
        visitData.timestamp = new Date().toISOString();
        
        const queue = this.getQueue();
        queue.push(visitData);
        localStorage.setItem(this.PROJECTS_KEY, JSON.stringify(queue));
        
        this.showToast('Visita guardada localmente (Offline)', 'warning');
        return true;
    },
    
    getQueue() {
        const item = localStorage.getItem(this.PROJECTS_KEY);
        return item ? JSON.parse(item) : [];
    },
    
    async syncPendingItems() {
        const queue = this.getQueue();
        if (queue.length === 0) return;
        
        console.log(`Attempting to sync ${queue.length} items...`);
        this.showToast(`Sincronizando ${queue.length} visitas pendientes...`, 'info');
        
        const remainingQueue = [];
        let syncedCount = 0;
        
        for (const visit of queue) {
            try {
                const response = await fetch('/api/visits/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(visit)
                });
                
                if (response.ok) {
                    syncedCount++;
                } else {
                    console.error('Server rejected visit:', visit);
                    remainingQueue.push(visit); // Keep in queue if server error
                }
            } catch (error) {
                console.error('Network error during sync:', error);
                remainingQueue.push(visit); // Keep in queue if network error
            }
        }
        
        localStorage.setItem(this.PROJECTS_KEY, JSON.stringify(remainingQueue));
        
        if (syncedCount > 0) {
            this.showToast(`${syncedCount} visitas sincronizadas con éxito.`, 'success');
            // Reload if on dashboard to show new items
            if (window.location.pathname === '/') {
                setTimeout(() => window.location.reload(), 1000);
            }
        }
    },
    
    showToast(msg, type='info') {
        // Simple usage of existing toast system logic if possible, or custom
        const toast = document.createElement('div');
        let colors = type === 'error' ? 'border-red-500' : (type === 'success' ? 'border-green-500' : 'border-blue-500');
        let icon = type === 'error' ? 'fa-circle-exclamation text-red-400' : (type === 'success' ? 'fa-check-circle text-green-400' : (type === 'warning' ? 'fa-triangle-exclamation text-yellow-400' : 'fa-info-circle text-blue-400'));
        
        toast.className = `toast-msg fade-in glass-card px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 border-l-4 ${colors} fixed top-4 right-4 z-50`;
        toast.innerHTML = `<i class="fas ${icon}"></i><span class="text-sm font-medium text-white">${msg}</span>`;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
};

document.addEventListener('DOMContentLoaded', () => OfflineManager.init());

"""Toma capturas de pantalla de la app para el manual."""
import asyncio
from playwright.async_api import async_playwright

BASE = "https://gestor-cartografico-app.onrender.com"
OUT = "docs/screenshots"

async def main():
    import os
    os.makedirs(OUT, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        # 1. Login page
        print("1. Login page...")
        await page.goto(f"{BASE}/login", wait_until="networkidle", timeout=120000)
        await page.screenshot(path=f"{OUT}/01_login.png")

        # Login
        print("   Logging in...")
        await page.fill('input[name="username"]', 'bgaleanotec')
        await page.fill('input[name="password"]', 'Vanti2026*')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        # 2. Dashboard
        print("2. Dashboard...")
        await page.screenshot(path=f"{OUT}/02_dashboard.png")

        # 3. Workflow
        print("3. Flujos de trabajo...")
        await page.goto(f"{BASE}/workflow/", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/03_workflow.png")

        # 4. Backlog
        print("4. Backlog...")
        await page.goto(f"{BASE}/backlog/", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/04_backlog.png")

        # 5. Ruta optima
        print("5. Ruta optima...")
        await page.goto(f"{BASE}/backlog/route", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/05_ruta_optima.png")

        # 6. Cartografia inbox
        print("6. Cartografia...")
        await page.goto(f"{BASE}/cartography/inbox", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/06_cartografia.png")

        # 7. Campo Lite mobile
        print("7. Campo Lite...")
        mobile_ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto(f"{BASE}/login", wait_until="networkidle", timeout=120000)
        await mobile_page.fill('input[name="username"]', 'bgaleanotec')
        await mobile_page.fill('input[name="password"]', 'Vanti2026*')
        await mobile_page.click('button[type="submit"]')
        await mobile_page.wait_for_load_state("networkidle")
        await mobile_page.goto(f"{BASE}/mobile/field", wait_until="networkidle", timeout=60000)
        await mobile_page.screenshot(path=f"{OUT}/07_campo_lite.png")

        # 8. SuperAdmin
        print("8. SuperAdmin...")
        await page.goto(f"{BASE}/superadmin/", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/08_superadmin.png")

        # 9. Proyectos dashboard
        print("9. Proyectos...")
        await page.goto(f"{BASE}/projects/dashboard", wait_until="networkidle", timeout=60000)
        await page.screenshot(path=f"{OUT}/09_proyectos.png")

        await browser.close()
        print(f"\nScreenshots guardados en {OUT}/")

asyncio.run(main())

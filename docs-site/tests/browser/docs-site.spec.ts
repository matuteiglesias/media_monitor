import { expect, test, type Page } from '@playwright/test'

const runtimeErrors: string[] = []
function monitorRuntime(page: Page) {
  page.on('pageerror', error => runtimeErrors.push(`pageerror: ${error.message}`))
  page.on('console', message => {
    const expectedNotFoundResponse = page.url().includes('route-that-does-not-exist') && message.text().includes('status of 404')
    if (message.type() === 'error' && !expectedNotFoundResponse) runtimeErrors.push(`console: ${message.text()}`)
  })
  page.on('requestfailed', request => {
    // Navigation/reload legitimately cancels in-flight lazy chunks; HTTP and network failures remain errors.
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') runtimeErrors.push(`request: ${request.url()} ${request.failure()?.errorText}`)
  })
}
test.beforeEach(async ({ page }) => { runtimeErrors.length = 0; monitorRuntime(page) })
test.afterEach(() => expect(runtimeErrors, runtimeErrors.join('\n')).toEqual([]))

test('navigates with header, sidebar, cards, and browser history', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.mermaid svg')).toBeVisible()
  await page.locator('.lane-card[href="/architecture/system-overview"]').click()
  await expect(page).toHaveURL(/\/architecture\/system-overview$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('System overview')
  await expect(page.locator('.mermaid svg')).toBeVisible()
  await page.getByRole('link', { name: 'Operations', exact: true }).first().click()
  await expect(page).toHaveURL(/\/operations\/?$/)
  await page.getByRole('link', { name: 'Sensing bundles', exact: true }).click()
  await expect(page).toHaveURL(/\/operations\/sensing-run-bundles$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('sensing run bundles')
  await page.goBack(); await expect(page).toHaveURL(/\/operations\/?$/)
  await page.goForward(); await expect(page).toHaveURL(/\/operations\/sensing-run-bundles$/)
  await page.goto('/')
  await page.locator('.lane-card[href="/case-studies/aws-immutable-sensing-retrofit"]').click()
  await expect(page).toHaveURL(/\/case-studies\/aws-immutable-sensing-retrofit$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('AWS immutable sensing retrofit')
})

test('loads, refreshes, and follows an in-document deep link', async ({ page }) => {
  await page.goto('/architecture/system-overview')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('System overview')
  await page.reload(); await expect(page.locator('.mermaid svg')).toBeVisible()
  const link = page.locator('.VPDocOutlineItem a').first()
  const target = await link.getAttribute('href')
  await link.click(); await expect(page).toHaveURL(new RegExp(`${target!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`))
})

test('serves the custom not-found page', async ({ page }) => {
  const response = await page.goto('/route-that-does-not-exist')
  expect(response?.status()).toBe(404)
  await expect(page.getByText('Signal lost.')).toBeVisible()
})

test('renders Mermaid in light and dark mode without breaking navigation', async ({ page }) => {
  await page.goto('/architecture/artifact-ladder-and-state')
  await expect(page.locator('.mermaid svg')).toBeVisible()
  await page.locator('.VPSwitchAppearance').first().click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await expect(page.locator('.mermaid svg')).toBeVisible()
  await page.getByRole('link', { name: 'Trust boundaries', exact: true }).first().click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Trust and mutation boundaries')
})

test('supports mobile navigation at 390px', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/')
  await page.locator('.VPNavBarHamburger').click()
  await page.locator('.VPNavScreen').getByRole('link', { name: 'System', exact: true }).click()
  await expect(page).toHaveURL(/\/system\/?$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('System')
})

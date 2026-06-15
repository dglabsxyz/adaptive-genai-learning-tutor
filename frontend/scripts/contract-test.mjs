import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const app = readFileSync(join(root, 'src', 'App.jsx'), 'utf8')

const required = [
  "['learner', 'educator', 'admin', 'sources']",
  '/cohort/progress',
  '/cohort/interventions',
  '/admin/source-quality',
  '/admin/index-status',
  '/admin/audit-events',
  'x-tutor-tenant-id',
  'x-tutor-role',
]

const missing = required.filter((needle) => !app.includes(needle))
if (missing.length) {
  console.error(`Missing frontend contracts: ${missing.join(', ')}`)
  process.exit(1)
}

console.log('frontend contract ok')

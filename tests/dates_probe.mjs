/**
 * Runs the frontend's date helpers and prints the results as JSON, so the
 * Python suite can assert on them without the project taking on a second
 * test runner. Node 24 strips the TypeScript types on import.
 *
 * Called by tests/test_dates.py. The cases live there, not here.
 */
import { readFileSync } from 'node:fs'
import * as dates from '../frontend/src/dates.ts'

const cases = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const today = cases.today ? new Date(...cases.today) : undefined

const out = cases.calls.map(([fn, ...args]) =>
  fn === 'awayFrom' || fn === 'deadline'
    ? dates[fn](args[0], today)
    : dates[fn](...args),
)
process.stdout.write(JSON.stringify(out))

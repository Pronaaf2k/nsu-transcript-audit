/**
 * scan_load.js — k6 load test for the NSU Transcript Audit Edge Function.
 * Simulates 20 concurrent users each uploading a CSV transcript.
 *
 * Run locally:
 *   k6 run --env SUPABASE_URL=... --env SUPABASE_ANON_KEY=... load-tests/scan_load.js
 *
 * Run in CI: see .github/workflows/load-test.yml
 */
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Trend, Counter } from 'k6/metrics'

// ── Custom metrics ────────────────────────────────────────────
export const auditDuration = new Trend('audit_duration_ms', true)
export const auditErrors = new Counter('audit_errors')

// ── Options ───────────────────────────────────────────────────
export const options = {
    scenarios: {
        concurrent_users: {
            executor: 'constant-vus',
            vus: 20,
            duration: '60s',
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<8000'],   // 95% of requests under 8s
        http_req_failed: ['rate<0.05'],    // < 5% error rate
        audit_duration_ms: ['p(50)<5000'],   // median audit under 5s
    },
}

// ── Minimal CSV transcript ────────────────────────────────────
const SAMPLE_CSV = `CourseID,CourseName,Credits,Grade,Semester,Attempt
CSE115,Intro to CS,3,A,Fall2020,1
CSE215,OOP,3,B+,Spring2021,1
CSE225,Data Structures,3,A-,Fall2021,1
MAT120,Calculus,3,B,Fall2020,1
MAT220,Linear Algebra,3,C+,Spring2021,1
ENG101,English,3,A,Fall2020,1
ENG102,English 2,3,B+,Spring2021,1
CSE311,Algorithms,3,B+,Fall2022,1
CSE331,Software Engineering,3,A,Spring2022,1
CSE411,AI,3,A-,Fall2023,1
CSE421,Machine Learning,3,B,Spring2023,1
CSE431,Computer Networks,3,C+,Fall2023,1
PHY101,Physics,3,B+,Fall2020,1
PHY102,Physics 2,3,B,Spring2021,1
CSE499,Capstone,3,A,Fall2024,1
`

const SUPABASE_URL = __ENV.SUPABASE_URL
const SUPABASE_ANON_KEY = __ENV.SUPABASE_ANON_KEY
// For load testing, use a pre-generated test user JWT
const TEST_JWT = __ENV.TEST_USER_JWT ?? SUPABASE_ANON_KEY

export default function () {
    const start = Date.now()

    const res = http.post(
        `${SUPABASE_URL}/functions/v1/process-transcript`,
        JSON.stringify({ csv_text: SAMPLE_CSV, program: 'CSE', file_name: 'load_test.csv' }),
        {
            headers: {
                Authorization: `Bearer ${TEST_JWT}`,
                'Content-Type': 'application/json',
            },
            timeout: '15s',
        }
    )

    const elapsed = Date.now() - start
    auditDuration.add(elapsed)

    const ok = check(res, {
        'status is 200': r => r.status === 200,
        'has scan result': r => {
            try { return !!JSON.parse(r.body).scan } catch { return false }
        },
        'response < 10s': r => r.timings.duration < 10000,
    })

    if (!ok) auditErrors.add(1)

    sleep(Math.random() * 2 + 1) // 1–3s think time between requests
}

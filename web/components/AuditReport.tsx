interface AuditScan {
    audit_result?: {
        l1?: { total_credits?: number }
        l2?: { cgpa?: number }
        l3?: { graduation_eligible?: boolean; deficiencies?: string[] }
        graduation_status?: string
    }
    program?: string
    graduation_status?: string
    total_credits?: number
    cgpa?: number
    created_at?: string
}

export default function AuditReport({ scan }: { scan: AuditScan }) {
    const ar = scan.audit_result ?? {}
    const status = scan.graduation_status ?? ar.graduation_status ?? 'PENDING'
    const credits = scan.total_credits ?? ar.l1?.total_credits ?? '—'
    const cgpa = scan.cgpa ?? ar.l2?.cgpa ?? '—'
    const deficiencies: string[] = ar.l3?.deficiencies ?? []

    const badgeClass =
        status === 'PASS' ? 'badge badge-pass' :
            status === 'FAIL' ? 'badge badge-fail' :
                'badge badge-pending'

    return (
        <div className="card animate-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Audit Result</h2>
                <span className={badgeClass}>{status}</span>
            </div>

            <div className="audit-grid">
                <div className="audit-stat">
                    <div className="val">{credits}</div>
                    <div className="lbl">Total Credits</div>
                </div>
                <div className="audit-stat">
                    <div className="val">{cgpa}</div>
                    <div className="lbl">CGPA</div>
                </div>
                <div className="audit-stat">
                    <div className="val">{scan.program ?? '—'}</div>
                    <div className="lbl">Program</div>
                </div>
            </div>

            {deficiencies.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--danger)', marginBottom: '10px' }}>
                        ⚠ Deficiencies
                    </h3>
                    <ul style={{ paddingLeft: '20px', color: 'var(--text-muted)' }}>
                        {deficiencies.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                </div>
            )}

            <details style={{ marginTop: '20px' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                    Raw JSON output
                </summary>
                <pre style={{
                    marginTop: '12px', background: 'var(--surface-2)', padding: '16px', borderRadius: '8px',
                    fontSize: '0.78rem', overflow: 'auto', color: 'var(--text-muted)'
                }}>
                    {JSON.stringify(ar, null, 2)}
                </pre>
            </details>
        </div>
    )
}

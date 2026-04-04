import Link from 'next/link'

interface Scan {
    id: string
    created_at: string
    source_type: string
    file_name?: string
    program?: string
    total_credits?: number
    cgpa?: number
    graduation_status?: string
}

export default function ScanHistoryTable({ scans }: { scans: Scan[] }) {
    return (
        <div className="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>File</th>
                        <th>Program</th>
                        <th>Credits</th>
                        <th>CGPA</th>
                        <th>Status</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {scans.map(s => (
                        <tr key={s.id}>
                            <td>{new Date(s.created_at).toLocaleDateString()}</td>
                            <td style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {s.file_name ?? `(${s.source_type})`}
                            </td>
                            <td>{s.program ?? '—'}</td>
                            <td>{s.total_credits ?? '—'}</td>
                            <td>{s.cgpa ?? '—'}</td>
                            <td>
                                <span className={
                                    s.graduation_status === 'PASS' ? 'badge badge-pass' :
                                        s.graduation_status === 'FAIL' ? 'badge badge-fail' :
                                            'badge badge-pending'
                                }>
                                    {s.graduation_status ?? 'PENDING'}
                                </span>
                            </td>
                            <td>
                                <Link href={`/report/${s.id}`} style={{ fontSize: '0.85rem' }}>View →</Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

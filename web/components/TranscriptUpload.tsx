'use client'

import { useRef, useState } from 'react'

interface Props {
    onUpload: (file: File) => void
    loading?: boolean
}

export default function TranscriptUpload({ onUpload, loading }: Props) {
    const inputRef = useRef<HTMLInputElement>(null)
    const [dragging, setDragging] = useState(false)
    const [fileName, setFileName] = useState<string | null>(null)

    function handleFile(file: File) {
        setFileName(file.name)
        onUpload(file)
    }

    return (
        <div>
            <div
                id="upload-zone"
                className={`upload-zone ${dragging ? 'drag-over' : ''}`}
                onClick={() => inputRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => {
                    e.preventDefault()
                    setDragging(false)
                    const f = e.dataTransfer.files[0]
                    if (f) handleFile(f)
                }}
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                {loading
                    ? <p>⏳ Processing…</p>
                    : fileName
                        ? <p>✅ {fileName} — <span style={{ color: 'var(--accent-2)' }}>click to change</span></p>
                        : <>
                            <p><strong>Drag & drop</strong> your transcript here</p>
                            <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>Supports PDF, JPG, PNG, CSV · click to browse</p>
                        </>
                }
            </div>
            <input
                ref={inputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.csv"
                style={{ display: 'none' }}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
            />
        </div>
    )
}

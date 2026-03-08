/**
 * Supabase Edge Function: process-transcript
 * Runtime: Deno
 *
 * All OCR is handled by Tesseract on the FastAPI server — free, unlimited.
 *
 * { csv_text, program }              → FastAPI /audit/csv
 * { storage_path, *.csv, program }   → FastAPI /audit/csv
 * { storage_path, image/pdf, prog }  → FastAPI /audit/image  (Tesseract)
 */

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const AUDIT_API_URL = Deno.env.get("AUDIT_API_URL") ?? "";  // https://nsu-audit-api.onrender.com
const AUDIT_API_KEY = Deno.env.get("AUDIT_API_KEY") ?? "";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuditResult {
    l1: Record<string, unknown>;
    l2: Record<string, unknown>;
    l3: Record<string, unknown>;
    program: string;
    graduation_status: "PASS" | "FAIL" | "PENDING";
    total_credits: number;
    cgpa: number;
}

const CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const PENDING = (program: string): AuditResult => ({
    l1: {}, l2: {}, l3: {}, program,
    graduation_status: "PENDING", total_credits: 0, cgpa: 0,
});

// ─── FastAPI helpers ──────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
    const h: Record<string, string> = {};
    if (AUDIT_API_KEY) h["Authorization"] = `Bearer ${AUDIT_API_KEY}`;
    return h;
}

/** Send CSV text to FastAPI /audit/csv */
async function auditWithCSV(csvText: string, program: string): Promise<AuditResult> {
    if (!AUDIT_API_URL) return PENDING(program);
    const form = new FormData();
    form.append("file", new Blob([csvText], { type: "text/csv" }), "transcript.csv");
    form.append("program", program);
    const res = await fetch(`${AUDIT_API_URL}/audit/csv`, {
        method: "POST", headers: authHeaders(), body: form,
    });
    if (!res.ok) throw new Error(`Audit API ${res.status}: ${await res.text()}`);
    return await res.json() as AuditResult;
}

/** Send raw image/PDF bytes to FastAPI /audit/image  (Tesseract on the server) */
async function auditWithImage(
    fileBytes: Uint8Array,
    fileName: string,
    program: string,
): Promise<AuditResult> {
    if (!AUDIT_API_URL) return PENDING(program);
    const ext = fileName.split(".").pop()?.toLowerCase() ?? "jpg";
    const mimeType = ext === "pdf" ? "application/pdf" : `image/${ext === "jpg" ? "jpeg" : ext}`;
    const form = new FormData();
    form.append("file", new Blob([fileBytes], { type: mimeType }), fileName);
    form.append("program", program);
    const res = await fetch(`${AUDIT_API_URL}/audit/image`, {
        method: "POST", headers: authHeaders(), body: form,
    });
    if (!res.ok) throw new Error(`Audit API ${res.status}: ${await res.text()}`);
    return await res.json() as AuditResult;
}

// ─── Main handler ─────────────────────────────────────────────────────────────

serve(async (req: Request) => {
    if (req.method === "OPTIONS") return new Response("ok", { headers: CORS_HEADERS });

    try {
        const authHeader = req.headers.get("Authorization");
        if (!authHeader) throw new Error("Missing Authorization header");

        const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
            global: { headers: { Authorization: authHeader } },
        });

        const { data: { user }, error: userErr } = await supabase.auth.getUser();
        if (userErr || !user) throw new Error("Unauthenticated");

        const body = await req.json();
        const { storage_path, program, csv_text, file_name } = body;
        if (!program) throw new Error("program is required");

        let auditResult: AuditResult;

        if (csv_text) {
            // ── Plain CSV text supplied directly ─────────────────────────
            auditResult = await auditWithCSV(csv_text, program);

        } else if (storage_path) {
            // ── Download from Supabase Storage then route by type ────────
            const { data: fileData, error: dlErr } = await supabase.storage
                .from("transcripts").download(storage_path);
            if (dlErr) throw dlErr;

            const bytes = new Uint8Array(await fileData.arrayBuffer());
            const fileName = (file_name ?? storage_path).split("/").pop() ?? "file";

            if (storage_path.toLowerCase().endsWith(".csv")) {
                auditResult = await auditWithCSV(new TextDecoder().decode(bytes), program);
            } else {
                // Image or PDF → Tesseract OCR on FastAPI server
                auditResult = await auditWithImage(bytes, fileName, program);
            }
        } else {
            throw new Error("Either storage_path or csv_text is required");
        }

        // ── Persist result to DB ─────────────────────────────────────────
        const { data: scan, error: insertErr } = await supabase
            .from("transcript_scans")
            .insert({
                user_id: user.id,
                source_type: csv_text ? "csv" : storage_path?.endsWith(".pdf") ? "pdf" : "image",
                storage_path: storage_path ?? null,
                file_name: file_name ?? null,
                audit_result: auditResult,
                program,
                total_credits: auditResult.total_credits,
                cgpa: auditResult.cgpa,
                graduation_status: auditResult.graduation_status,
            })
            .select()
            .single();

        if (insertErr) throw insertErr;

        return new Response(JSON.stringify({ scan }), {
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
            status: 200,
        });
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return new Response(JSON.stringify({ error: message }), {
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
            status: 400,
        });
    }
});

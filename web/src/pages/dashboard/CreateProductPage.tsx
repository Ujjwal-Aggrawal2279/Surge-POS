import { useState } from "react";
import { post } from "@/lib/api";
import { CheckCircle2, Loader2 } from "lucide-react";

interface FormState {
  item_code: string;
  item_name: string;
  item_group: string;
  stock_uom: string;
  description: string;
}

const INIT: FormState = { item_code: "", item_name: "", item_group: "All Item Groups", stock_uom: "Nos", description: "" };

export function CreateProductPage() {
  const [form, setForm] = useState<FormState>(INIT);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  function set(k: keyof FormState, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
    setSuccess("");
    setError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.item_name) { setError("Item name is required."); return; }
    setSaving(true);
    setError("");
    try {
      const res = await post<{ name?: string; exc_type?: string; exception?: string }>(
        "frappe.client.insert",
        { doc: { doctype: "Item", ...form } },
      );
      if (res.name) {
        setSuccess(`Item "${res.name}" created successfully.`);
        setForm(INIT);
      } else {
        setError(res.exception ?? "Failed to create item.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const field = (label: string, k: keyof FormState, required = false) => (
    <div>
      <label className="mb-1 block text-xs font-semibold text-[#212B36]">
        {label}{required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      <input
        value={form[k]}
        onChange={(e) => set(k, e.target.value)}
        className="w-full rounded-lg border border-[#E6EAED] px-3 py-2 text-sm outline-none focus:border-[#6938EF]"
      />
    </div>
  );

  return (
    <div className="max-w-lg">
      <h2 className="mb-6 text-lg font-bold text-[#212B36]">Create Product</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 rounded-2xl border border-[#E6EAED] bg-white p-6 shadow-sm">
        {field("Item Code", "item_code")}
        {field("Item Name", "item_name", true)}
        {field("Item Group", "item_group")}
        {field("Stock UOM", "stock_uom")}
        <div>
          <label className="mb-1 block text-xs font-semibold text-[#212B36]">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-[#E6EAED] px-3 py-2 text-sm outline-none focus:border-[#6938EF]"
          />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        {success && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4 shrink-0" />{success}
          </div>
        )}
        <button
          type="submit"
          disabled={saving}
          className="flex h-10 items-center justify-center gap-2 rounded-lg bg-[#6938EF] text-sm font-bold text-white disabled:opacity-40 hover:bg-[#5a2fd6]"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {saving ? "Creating…" : "Create Item"}
        </button>
      </form>
    </div>
  );
}

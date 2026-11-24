import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { Badge, Button, Card } from "../components/ui";
import {
  ApiError,
  getAdminAreas,
  getAdminDataSources,
  getAdminDatasets,
  getAdminObservations,
  getAllAdminDataSources,
  getAllAdminDatasets,
  saveAdminDataSource,
  saveAdminDataset,
  saveAdminObservation,
  type AdminDataSource,
  type AdminDataset,
  type AdminIndicatorObservation,
  type Area,
  type DataSourceWrite,
  type DatasetWrite,
  type InventoryFilters,
  type ObservationWrite,
  type PaginatedResponse,
} from "../services/api";
import {
  DataClassBadge,
  EmptyState,
  ErrorPanel,
  formatDate,
  LoadingPanel,
  PageHeading,
} from "./AppUI";

type AdminUserState = ReturnType<typeof useAuth>["state"];
type Loader<T> = (page: number, filters: InventoryFilters) => Promise<PaginatedResponse<T>>;

function isAdmin(state: AdminUserState) {
  return state.status === "ready" && state.user !== null && ["staff", "superuser"].includes(state.user.role);
}

function errorText(error: unknown) {
  if (error instanceof ApiError && typeof error.details === "object" && error.details !== null) {
    const fieldErrors = Object.entries(error.details)
      .map(([field, value]) => {
        const messages = Array.isArray(value) ? value.join(", ") : String(value);
        return `${field}: ${messages}`;
      })
      .join("; ");
    if (fieldErrors) return `${error.message} ${fieldErrors}`;
  }
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "The request could not be completed.";
}

function SummaryCards({ items }: { items: [string, number][] }) {
  return (
    <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map(([label, count]) => (
        <Card key={label} className="p-4">
          <p className="text-xs text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{count}</p>
        </Card>
      ))}
    </div>
  );
}

function useAdminRecords<T>(load: Loader<T>, filterKey: string) {
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; error: unknown }
    | { status: "ready"; data: PaginatedResponse<T> }
  >({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    const filters = JSON.parse(filterKey) as InventoryFilters;
    load(page, filters)
      .then((data) => {
        if (active) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (active) setState({ status: "error", error });
      });
    return () => {
      active = false;
    };
  }, [page, version, filterKey]);

  return {
    page,
    setPage,
    state,
    refresh: () => setVersion((current) => current + 1),
  };
}

function SearchAndFilter({
  search,
  onSearch,
  children,
}: {
  search: string;
  onSearch: (value: string) => void;
  children?: ReactNode;
}) {
  return (
    <Card className="mb-5 flex flex-wrap items-end gap-3 p-4">
      <label className="min-w-[14rem] flex-1 text-xs font-medium text-slate-400">
        Search records
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          className="mt-1.5 min-h-10 w-full rounded-lg border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
          placeholder="Search…"
        />
      </label>
      {children}
    </Card>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="min-w-36 text-xs font-medium text-slate-400">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 min-h-10 w-full rounded-lg border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
      >
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function InventoryCards<T>({
  state,
  emptyTitle,
  emptyDetail,
  page,
  setPage,
  renderRecord,
}: {
  state: ReturnType<typeof useAdminRecords<T>>["state"];
  emptyTitle: string;
  emptyDetail: string;
  page: number;
  setPage: (page: number | ((current: number) => number)) => void;
  renderRecord: (item: T) => ReactNode;
}) {
  if (state.status === "loading") return <LoadingPanel label="Loading administrative records…" />;
  if (state.status === "error") return <ErrorPanel error={state.error} />;
  if (!state.data.results.length) return <EmptyState title={emptyTitle} detail={emptyDetail} />;
  return (
    <>
      <p className="mb-3 text-sm text-slate-500">{state.data.count} records · page {page}</p>
      <div className="space-y-3">{state.data.results.map((item, index) => <div key={index}>{renderRecord(item)}</div>)}</div>
      <div className="mt-5 flex justify-end gap-3">
        <Button variant="secondary" disabled={!state.data.previous} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button>
        <Button variant="secondary" disabled={!state.data.next} onClick={() => setPage((value) => value + 1)}>Next</Button>
      </div>
    </>
  );
}

function EditorModal({
  title,
  saving,
  error,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/75 p-3 sm:p-6" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !saving) onClose();
    }}>
      <section role="dialog" aria-modal="true" aria-labelledby="admin-editor-title" className="max-h-[92dvh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/10 bg-[#080d1c] p-5 shadow-2xl sm:p-7">
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2 id="admin-editor-title" className="text-xl font-semibold text-white">{title}</h2>
          <button type="button" onClick={onClose} disabled={saving} className="grid h-9 w-9 place-items-center rounded-lg border border-white/10 text-slate-300 hover:bg-white/5" aria-label="Close form">×</button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          {children}
          {error && <p role="alert" className="rounded-lg border border-red-300/15 bg-red-300/5 p-3 text-sm text-red-100">{error}</p>}
          <div className="flex flex-wrap justify-end gap-3 border-t border-white/[0.07] pt-4">
            <Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save record"}</Button>
          </div>
        </form>
      </section>
    </div>
  );
}

function FormField({
  label,
  name,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder,
  children,
}: {
  label: string;
  name?: string;
  value?: string;
  onChange?: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  children?: ReactNode;
}) {
  return (
    <label className="block text-sm text-slate-300">
      {label}
      {children ?? (
        <input
          name={name}
          value={value}
          onChange={(event) => onChange?.(event.target.value)}
          type={type}
          required={required}
          placeholder={placeholder}
          className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
        />
      )}
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm text-slate-300">
      {label}
      <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={3} className="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100" />
    </label>
  );
}

function RecordActions({ onEdit }: { onEdit: () => void }) {
  return <Button variant="secondary" size="sm" onClick={onEdit}>View / edit</Button>;
}

export function AdminDataSourcesPage() {
  const [search, setSearch] = useState("");
  const [approval, setApproval] = useState("");
  const filters = { search, approval_status: approval || undefined };
  const resource = useAdminRecords<AdminDataSource>(getAdminDataSources, JSON.stringify(filters));
  const [counts, setCounts] = useState<{ total: number; approved: number; pending: number; rejected: number; other: number } | null>(null);
  const [summaryError, setSummaryError] = useState<unknown>(null);
  const [editing, setEditing] = useState<AdminDataSource | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState("");
  const [draft, setDraft] = useState<DataSourceWrite>({
    source_name: "", owner_name: "", official_url: "", licence_terms: "", approval_status: "PENDING",
  });

  useEffect(() => {
    let active = true;
    setSummaryError(null);
    getAllAdminDataSources().then(({ results }) => {
      if (!active) return;
      const counts = { total: results.length, approved: 0, pending: 0, rejected: 0, other: 0 };
      for (const source of results) {
        const status = source.approval_status.trim().toUpperCase();
        if (status === "APPROVED") counts.approved += 1;
        else if (status === "PENDING") counts.pending += 1;
        else if (status === "REJECTED") counts.rejected += 1;
        else counts.other += 1;
      }
      setCounts(counts);
    }).catch((error: unknown) => {
      if (active) {
        setCounts(null);
        setSummaryError(error);
      }
    });
    return () => { active = false; };
  }, [success]);

  function openEditor(item?: AdminDataSource) {
    setEditing(item ?? null);
    setError(null);
    setDraft(item ? {
      source_name: item.source_name,
      owner_name: item.owner_name,
      official_url: item.official_url ?? "",
      licence_terms: item.licence_terms ?? "",
      approval_status: item.approval_status as DataSourceWrite["approval_status"],
    } : { source_name: "", owner_name: "", official_url: "", licence_terms: "", approval_status: "PENDING" });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await saveAdminDataSource({ ...draft, official_url: draft.official_url || null, licence_terms: draft.licence_terms || null }, editing?.id);
      setSuccess(editing ? "Source updated successfully." : "Source created successfully.");
      setEditing(undefined);
      resource.refresh();
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeading title="Data Sources" description="Manage environmental data providers, ownership and source approval." action={<Button onClick={() => openEditor()}>Add Data Source</Button>} />
      {summaryError !== null && <ErrorPanel error={summaryError} />}
      {counts && <SummaryCards items={[
        ["Total sources", counts.total],
        ["Approved", counts.approved],
        ["Pending", counts.pending],
        ["Rejected", counts.rejected],
        ...(counts.other ? [["Other status", counts.other] as [string, number]] : []),
      ]} />}
      {success && <p role="status" className="mb-4 text-sm text-emerald-200">{success}</p>}
      <SearchAndFilter search={search} onSearch={(value) => { setSearch(value); resource.setPage(1); }}>
        <FilterSelect label="Approval" value={approval} onChange={(value) => { setApproval(value); resource.setPage(1); }} options={[{ value: "", label: "All statuses" }, { value: "PENDING", label: "Pending" }, { value: "APPROVED", label: "Approved" }, { value: "REJECTED", label: "Rejected" }]} />
      </SearchAndFilter>
      <InventoryCards state={resource.state} emptyTitle="No data sources found" emptyDetail="Create a source record to begin the provenance workflow." page={resource.page} setPage={resource.setPage} renderRecord={(item) => (
        <Card className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="min-w-0"><h3 className="font-semibold text-white">{item.source_name}</h3><p className="mt-1 text-sm text-slate-400">{item.owner_name} · Created {formatDate(item.created_at)}</p><p className="mt-1 break-all text-xs text-slate-500">{item.official_url || "No official URL provided"}</p></div>
          <div className="flex items-center gap-3"><Badge variant={item.approval_status === "APPROVED" ? "green" : item.approval_status === "REJECTED" ? "red" : "orange"}>{item.approval_status}</Badge><RecordActions onEdit={() => openEditor(item)} /></div>
        </Card>
      )} />
      {editing !== undefined && <EditorModal title={editing ? "View / edit data source" : "Add data source"} saving={saving} error={error} onClose={() => setEditing(undefined)} onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Source name" value={draft.source_name} onChange={(value) => setDraft({ ...draft, source_name: value })} required />
          <FormField label="Owner / organization" value={draft.owner_name} onChange={(value) => setDraft({ ...draft, owner_name: value })} required />
        </div>
        <FormField label="Official URL" type="url" value={draft.official_url ?? ""} onChange={(value) => setDraft({ ...draft, official_url: value })} placeholder="https://" />
        <TextAreaField label="Licence terms (administrative)" value={draft.licence_terms ?? ""} onChange={(value) => setDraft({ ...draft, licence_terms: value })} />
        <FilterSelect label="Approval status" value={draft.approval_status} onChange={(value) => setDraft({ ...draft, approval_status: value as DataSourceWrite["approval_status"] })} options={[{ value: "PENDING", label: "Pending" }, { value: "APPROVED", label: "Approved" }, { value: "REJECTED", label: "Rejected" }]} />
      </EditorModal>}
    </>
  );
}

function AdminPageGuard({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  return isAdmin(state) ? <>{children}</> : <ErrorPanel error={new Error("Administrator access is required to manage records.")} />;
}

export function AdminDatasetsPage() {
  const [search, setSearch] = useState("");
  const [dataClass, setDataClass] = useState("");
  const [active, setActive] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const filters = {
    search,
    source_id: sourceFilter ? Number(sourceFilter) : undefined,
    data_class: dataClass || undefined,
    is_active: active === "" ? undefined : active === "true",
  };
  const resource = useAdminRecords<AdminDataset>(getAdminDatasets, JSON.stringify(filters));
  const [sources, setSources] = useState<AdminDataSource[]>([]);
  const [sourcesLoaded, setSourcesLoaded] = useState(false);
  const [sourceError, setSourceError] = useState<unknown>(null);
  const [counts, setCounts] = useState<number[] | null>(null);
  const [summaryError, setSummaryError] = useState<unknown>(null);
  const [editing, setEditing] = useState<AdminDataset | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState("");
  const [draft, setDraft] = useState<DatasetWrite>({
    source: 0, dataset_name: "", data_class: "observed", spatial_resolution: "",
    published_at: null, coverage_start: null, coverage_end: null, retrieved_at: "",
    file_hash: null, transformation_notes: null, is_active: false,
  });
  useEffect(() => {
    let active = true;
    getAllAdminDataSources()
      .then((response) => {
        if (active) {
          setSources(response.results);
          setSourceError(null);
          setSourcesLoaded(true);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setSourceError(error);
          setSourcesLoaded(true);
        }
      });
    return () => { active = false; };
  }, [success]);

  useEffect(() => {
    let active = true;
    setSummaryError(null);
    Promise.all([
      getAdminDatasets(1),
      getAdminDatasets(1, { is_active: true }),
      getAdminDatasets(1, { is_active: false }),
      getAdminDatasets(1, { data_class: "observed" }),
      getAdminDatasets(1, { data_class: "derived" }),
      getAdminDatasets(1, { data_class: "illustrative" }),
    ]).then((responses) => {
      if (active) setCounts(responses.map((response) => response.count));
    }).catch((error: unknown) => {
      if (active) {
        setCounts(null);
        setSummaryError(error);
      }
    });
    return () => { active = false; };
  }, [success]);

  function openEditor(item?: AdminDataset) {
    setEditing(item ?? null);
    setError(null);
    setDraft(item ? {
      source: item.source, dataset_name: item.dataset_name, data_class: item.data_class as DatasetWrite["data_class"],
      spatial_resolution: item.spatial_resolution, published_at: item.published_at,
      coverage_start: item.coverage_start, coverage_end: item.coverage_end,
      retrieved_at: item.retrieved_at.slice(0, 16), file_hash: item.file_hash,
      transformation_notes: item.transformation_notes, is_active: item.is_active,
    } : {
      source: 0, dataset_name: "", data_class: "observed", spatial_resolution: "",
      published_at: null, coverage_start: null, coverage_end: null, retrieved_at: "",
      file_hash: null, transformation_notes: null, is_active: false,
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    if (draft.coverage_start && draft.coverage_end && draft.coverage_start > draft.coverage_end) {
      setError("Coverage end cannot precede coverage start.");
      return;
    }
    setSaving(true); setError(null);
    try {
      await saveAdminDataset({
        ...draft,
        published_at: draft.published_at || null,
        coverage_start: draft.coverage_start || null,
        coverage_end: draft.coverage_end || null,
        retrieved_at: new Date(draft.retrieved_at).toISOString(),
        file_hash: draft.file_hash || null,
        transformation_notes: draft.transformation_notes || null,
      }, editing?.id);
      setSuccess(editing ? "Dataset updated successfully." : "Dataset created successfully.");
      setEditing(undefined); resource.refresh();
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }

  const eligibleSources = sources.filter((source) => source.approval_status.toUpperCase() === "APPROVED");
  return (
    <AdminPageGuard>
      <PageHeading title="Datasets" description="Manage environmental datasets and their source provenance." action={<Button disabled={!sourcesLoaded || Boolean(sourceError) || !eligibleSources.length} onClick={() => openEditor()}>Add dataset</Button>} />
      {summaryError !== null && <ErrorPanel error={summaryError} />}
      {counts && <SummaryCards items={[
        ["Total datasets", counts[0]],
        ["Active", counts[1]],
        ["Inactive", counts[2]],
        ["Observed", counts[3]],
        ["Derived", counts[4]],
        ["Illustrative", counts[5]],
      ]} />}
      {success && <p role="status" className="mb-4 text-sm text-emerald-200">{success}</p>}
      <SearchAndFilter search={search} onSearch={(value) => { setSearch(value); resource.setPage(1); }}>
        <FilterSelect label="Source" value={sourceFilter} onChange={(value) => { setSourceFilter(value); resource.setPage(1); }} options={[{ value: "", label: "All sources" }, ...sources.map((source) => ({ value: String(source.id), label: source.source_name }))]} />
        <FilterSelect label="Data class" value={dataClass} onChange={(value) => { setDataClass(value); resource.setPage(1); }} options={[{ value: "", label: "All classes" }, ...["observed", "derived", "illustrative"].map((value) => ({ value, label: value }))]} />
        <FilterSelect label="Active status" value={active} onChange={(value) => { setActive(value); resource.setPage(1); }} options={[{ value: "", label: "All states" }, { value: "true", label: "Active" }, { value: "false", label: "Inactive" }]} />
      </SearchAndFilter>
      {sourceError !== null && <ErrorPanel error={sourceError} />}
      {sourcesLoaded && !sourceError && !eligibleSources.length && <Card className="mb-4 p-4 text-sm text-slate-300">No approved data source is available. Create or approve a data source before adding a dataset. <a className="text-cyan-200 underline" href="/app/data-sources">Go to Data Sources</a>.</Card>}
      <InventoryCards state={resource.state} emptyTitle="No datasets found" emptyDetail="Create a dataset from an approved source. Datasets do not create observations automatically." page={resource.page} setPage={resource.setPage} renderRecord={(item) => (
        <Card className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="min-w-0"><h3 className="font-semibold text-white">{item.dataset_name}</h3><p className="mt-1 text-sm text-slate-400">{item.source_name} · {item.spatial_resolution}</p><p className="mt-1 text-xs text-slate-500">Coverage {item.coverage_start ?? "unspecified"} – {item.coverage_end ?? "unspecified"} · Published {item.published_at ?? "unspecified"} · Retrieved {formatDate(item.retrieved_at)}</p><div className="mt-2 flex flex-wrap gap-2"><DataClassBadge value={item.data_class} /><Badge variant={item.is_active ? "green" : "neutral"}>{item.is_active ? "Active" : "Inactive"}</Badge></div></div>
          <RecordActions onEdit={() => openEditor(item)} />
        </Card>
      )} />
      {editing !== undefined && <EditorModal title={editing ? "View / edit dataset" : "Add dataset"} saving={saving} error={error} onClose={() => setEditing(undefined)} onSubmit={submit}>
        {!eligibleSources.length ? <p className="text-sm text-amber-100">An approved source is required before a dataset can be saved.</p> : <FormField label="Data source" required><select required value={draft.source || ""} onChange={(event) => setDraft({ ...draft, source: Number(event.target.value) })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"><option value="">Select approved source</option>{eligibleSources.map((item) => <option key={item.id} value={item.id}>{item.source_name} — {item.owner_name}</option>)}</select></FormField>}
        <FormField label="Dataset name" value={draft.dataset_name} onChange={(value) => setDraft({ ...draft, dataset_name: value })} required />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Data class"><select value={draft.data_class} onChange={(event) => setDraft({ ...draft, data_class: event.target.value as DatasetWrite["data_class"] })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100">{["observed", "derived", "illustrative"].map((item) => <option key={item}>{item}</option>)}</select></FormField>
          <FormField label="Spatial resolution" value={draft.spatial_resolution} onChange={(value) => setDraft({ ...draft, spatial_resolution: value })} required />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Publication date" type="date" value={draft.published_at ?? ""} onChange={(value) => setDraft({ ...draft, published_at: value || null })} />
          <FormField label="Retrieved at" type="datetime-local" value={draft.retrieved_at} onChange={(value) => setDraft({ ...draft, retrieved_at: value })} required />
          <FormField label="Coverage start" type="date" value={draft.coverage_start ?? ""} onChange={(value) => setDraft({ ...draft, coverage_start: value || null })} />
          <FormField label="Coverage end" type="date" value={draft.coverage_end ?? ""} onChange={(value) => setDraft({ ...draft, coverage_end: value || null })} />
        </div>
        <FormField label="File hash (if applicable)" value={draft.file_hash ?? ""} onChange={(value) => setDraft({ ...draft, file_hash: value || null })} />
        <TextAreaField label="Transformation notes (administrative)" value={draft.transformation_notes ?? ""} onChange={(value) => setDraft({ ...draft, transformation_notes: value || null })} />
        <label className="flex items-center gap-3 text-sm text-slate-300"><input type="checkbox" checked={draft.is_active} onChange={(event) => setDraft({ ...draft, is_active: event.target.checked })} /> Active for observation ingestion and assessment use</label>
      </EditorModal>}
    </AdminPageGuard>
  );
}

const indicatorOptions = [
  { code: "AIR_TEMPERATURE", unit: "degree_celsius" },
  { code: "RELATIVE_HUMIDITY", unit: "percent" },
  { code: "RAINFALL_24H", unit: "mm" },
];

function qualityVariant(status: string) {
  if (status === "VALID") return "green" as const;
  if (status === "INVALID") return "red" as const;
  if (status === "MISSING") return "neutral" as const;
  return "orange" as const;
}

export function AdminObservationsPage() {
  const [search, setSearch] = useState("");
  const [indicator, setIndicator] = useState("");
  const [quality, setQuality] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [datasetFilter, setDatasetFilter] = useState("");
  const filters = {
    search,
    indicator_code: indicator || undefined,
    quality_status: quality || undefined,
    area_id: areaFilter ? Number(areaFilter) : undefined,
    dataset_id: datasetFilter ? Number(datasetFilter) : undefined,
  };
  const resource = useAdminRecords<AdminIndicatorObservation>(getAdminObservations, JSON.stringify(filters));
  const [areas, setAreas] = useState<Area[]>([]);
  const [datasets, setDatasets] = useState<AdminDataset[]>([]);
  const [referencesLoaded, setReferencesLoaded] = useState(false);
  const [referenceError, setReferenceError] = useState<unknown>(null);
  const [counts, setCounts] = useState<number[] | null>(null);
  const [summaryError, setSummaryError] = useState<unknown>(null);
  const [editing, setEditing] = useState<AdminIndicatorObservation | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState("");
  const [draft, setDraft] = useState<ObservationWrite>({
    area: 0, dataset: 0, indicator_code: "AIR_TEMPERATURE", period_start: "", period_end: "",
    raw_value_numeric: "", raw_value_text: null, raw_unit: "degree_celsius",
    quality_status: "VALID", notes: null,
  });
  useEffect(() => {
    let active = true;
    Promise.all([getAdminAreas(), getAllAdminDatasets()])
      .then(([areaResponse, datasetResponse]) => {
        if (active) {
          setAreas(areaResponse.results);
          setDatasets(datasetResponse.results);
          setReferenceError(null);
          setReferencesLoaded(true);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setReferenceError(error);
          setReferencesLoaded(true);
        }
      });
    return () => { active = false; };
  }, [success]);

  useEffect(() => {
    let active = true;
    setSummaryError(null);
    Promise.all([
      getAdminObservations(1),
      getAdminObservations(1, { indicator_code: "AIR_TEMPERATURE" }),
      getAdminObservations(1, { indicator_code: "RELATIVE_HUMIDITY" }),
      getAdminObservations(1, { indicator_code: "RAINFALL_24H" }),
    ]).then((responses) => {
      if (active) setCounts(responses.map((response) => response.count));
    }).catch((error: unknown) => {
      if (active) {
        setCounts(null);
        setSummaryError(error);
      }
    });
    return () => { active = false; };
  }, [success]);

  const eligibleDatasets = datasets.filter((item) => item.is_active && item.source_approval_status.toUpperCase() === "APPROVED");

  function openEditor(item?: AdminIndicatorObservation) {
    setEditing(item ?? null); setError(null);
    setDraft(item ? {
      area: item.area, dataset: item.dataset, indicator_code: item.indicator_code,
      period_start: item.period_start, period_end: item.period_end,
      raw_value_numeric: item.raw_value_numeric, raw_value_text: item.raw_value_text,
      raw_unit: item.raw_unit, quality_status: item.quality_status, notes: item.notes,
    } : {
      area: 0, dataset: 0, indicator_code: "AIR_TEMPERATURE", period_start: "", period_end: "",
      raw_value_numeric: "", raw_value_text: null, raw_unit: "degree_celsius",
      quality_status: "VALID", notes: null,
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    if (draft.period_start && draft.period_end && draft.period_start > draft.period_end) {
      setError("Period end cannot precede period start.");
      return;
    }
    setSaving(true); setError(null);
    try {
      await saveAdminObservation({
        ...draft,
        area: Number(draft.area), dataset: Number(draft.dataset),
        raw_value_numeric: draft.raw_value_numeric || null,
        raw_value_text: draft.raw_value_text || null,
        raw_unit: draft.raw_unit || null,
        notes: draft.notes || null,
      }, editing?.id);
      setSuccess(editing ? "Observation updated successfully." : "Observation saved successfully.");
      setEditing(undefined); resource.refresh();
    } catch (requestError) { setError(errorText(requestError)); }
    finally { setSaving(false); }
  }

  const selectedIndicator = indicatorOptions.find((item) => item.code === draft.indicator_code);
  return (
    <AdminPageGuard>
      <PageHeading title="Indicator Observations" description="Manage measured environmental values, locations, periods and quality information." action={<Button disabled={!referencesLoaded || Boolean(referenceError) || !eligibleDatasets.length} onClick={() => openEditor()}>Add observation</Button>} />
      {summaryError !== null && <ErrorPanel error={summaryError} />}
      {counts && <SummaryCards items={[
        ["Total observations", counts[0]],
        ["Temperature", counts[1]],
        ["Humidity", counts[2]],
        ["Rainfall", counts[3]],
        ...(counts[0] > counts[1] + counts[2] + counts[3]
          ? [["Other indicators", counts[0] - counts[1] - counts[2] - counts[3]] as [string, number]]
          : []),
      ]} />}
      {success && <p role="status" className="mb-4 text-sm text-emerald-200">{success}</p>}
      <SearchAndFilter search={search} onSearch={(value) => { setSearch(value); resource.setPage(1); }}>
        <FilterSelect label="Indicator" value={indicator} onChange={(value) => { setIndicator(value); resource.setPage(1); }} options={[{ value: "", label: "All indicators" }, ...indicatorOptions.map(({ code }) => ({ value: code, label: code.replaceAll("_", " ") }))]} />
        <FilterSelect label="Quality" value={quality} onChange={(value) => { setQuality(value); resource.setPage(1); }} options={[{ value: "", label: "All quality states" }, ...["VALID", "MISSING", "INVALID", "STALE", "LOW_CONFIDENCE", "NOT_APPLICABLE", "PENDING_REVIEW"].map((value) => ({ value, label: value.replaceAll("_", " ") }))]} />
        <FilterSelect label="Location" value={areaFilter} onChange={(value) => { setAreaFilter(value); resource.setPage(1); }} options={[{ value: "", label: "All locations" }, ...areas.map((area) => ({ value: String(area.id), label: `${area.city.name} — ${area.area_name}` }))]} />
        <FilterSelect label="Dataset" value={datasetFilter} onChange={(value) => { setDatasetFilter(value); resource.setPage(1); }} options={[{ value: "", label: "All datasets" }, ...datasets.map((dataset) => ({ value: String(dataset.id), label: dataset.dataset_name }))]} />
      </SearchAndFilter>
      {referenceError !== null && <ErrorPanel error={referenceError} />}
      {referencesLoaded && !referenceError && !eligibleDatasets.length && <Card className="mb-4 p-4 text-sm text-slate-300">No active dataset linked to an approved source is available. <a className="text-cyan-200 underline" href="/app/datasets">Review datasets</a>.</Card>}
      <InventoryCards state={resource.state} emptyTitle="No observations found" emptyDetail="No stored observation records match these filters. Add records with their actual dataset, location, period and quality." page={resource.page} setPage={resource.setPage} renderRecord={(item) => (
        <Card className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="min-w-0"><h3 className="font-semibold text-white">{item.indicator_code} · {item.area_name}, {item.city_name}</h3><p className="mt-1 text-sm text-slate-400">{item.raw_value_numeric ?? item.raw_value_text ?? "Missing value"} {item.raw_unit ?? ""} · {item.dataset_name}</p><p className="mt-1 text-xs text-slate-500">{item.period_start} – {item.period_end}</p><div className="mt-2"><DataClassBadge value={item.data_class} /></div></div>
          <div className="flex items-center gap-3"><Badge variant={qualityVariant(item.quality_status)}>{item.quality_status.replaceAll("_", " ")}</Badge><RecordActions onEdit={() => openEditor(item)} /></div>
        </Card>
      )} />
      {editing !== undefined && <EditorModal title={editing ? "View / edit observation" : "Add observation"} saving={saving} error={error} onClose={() => setEditing(undefined)} onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Area" required><select required value={draft.area || ""} onChange={(event) => setDraft({ ...draft, area: Number(event.target.value) })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"><option value="">Select area</option>{areas.map((area) => <option key={area.id} value={area.id}>{area.city.name} — {area.area_name} ({area.area_type})</option>)}</select></FormField>
          <FormField label="Dataset" required><select required value={draft.dataset || ""} onChange={(event) => setDraft({ ...draft, dataset: Number(event.target.value) })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"><option value="">Select active approved dataset</option>{eligibleDatasets.map((item) => <option key={item.id} value={item.id}>{item.dataset_name} — {item.source_name}</option>)}</select></FormField>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Indicator" required><select value={draft.indicator_code} onChange={(event) => { const code = event.target.value; setDraft({ ...draft, indicator_code: code, raw_unit: indicatorOptions.find((item) => item.code === code)?.unit ?? "" }); }} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100">{indicatorOptions.map((item) => <option key={item.code} value={item.code}>{item.code.replaceAll("_", " ")}</option>)}</select></FormField>
          <FormField label="Quality status" required><select value={draft.quality_status} onChange={(event) => setDraft({ ...draft, quality_status: event.target.value })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100">{["VALID", "MISSING", "INVALID", "STALE", "LOW_CONFIDENCE", "NOT_APPLICABLE", "PENDING_REVIEW"].map((item) => <option key={item}>{item}</option>)}</select></FormField>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Period start" type="date" value={draft.period_start} onChange={(value) => setDraft({ ...draft, period_start: value })} required />
          <FormField label="Period end" type="date" value={draft.period_end} onChange={(value) => setDraft({ ...draft, period_end: value })} required />
          <FormField label="Numeric value" type="number" value={draft.raw_value_numeric ?? ""} onChange={(value) => setDraft({ ...draft, raw_value_numeric: value || null, raw_value_text: value ? null : draft.raw_value_text })} placeholder="Leave blank if unavailable" />
          <FormField label="Unit" required={draft.raw_value_numeric !== null}><select value={draft.raw_unit ?? ""} onChange={(event) => setDraft({ ...draft, raw_unit: event.target.value || null })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"><option value="">Select unit</option>{selectedIndicator && <option value={selectedIndicator.unit}>{selectedIndicator.unit}</option>}</select></FormField>
        </div>
        <FormField label="Text value (alternative to numeric)"><input value={draft.raw_value_text ?? ""} onChange={(event) => setDraft({ ...draft, raw_value_text: event.target.value || null, raw_value_numeric: event.target.value ? null : draft.raw_value_numeric })} className="mt-1.5 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100" /></FormField>
        <p className="text-xs leading-5 text-slate-500">A value may be omitted only when quality status is MISSING. Units are validated for the selected indicator ({selectedIndicator?.unit ?? "—"}).</p>
        <TextAreaField label="Administrative notes" value={draft.notes ?? ""} onChange={(value) => setDraft({ ...draft, notes: value || null })} />
      </EditorModal>}
    </AdminPageGuard>
  );
}

export function AdminDataSourcesRoute() {
  const { state } = useAuth();
  return isAdmin(state) ? <AdminDataSourcesPage /> : null;
}

export const AdminDatasetsRoute = AdminDatasetsPage;
export const AdminObservationsRoute = AdminObservationsPage;

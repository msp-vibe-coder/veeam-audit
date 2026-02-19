import { useState, useEffect, useCallback, useRef } from "react";
import { Save, CheckCircle2, AlertCircle, Play, RefreshCw } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fetchSettings, updateSettings, fetchPipelineStatus, triggerPipeline } from "@/lib/api";
import Card from "@/components/ui/Card";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { Settings as SettingsType, PipelineStatus } from "@/types";

export default function Settings() {
  const { data: settings, loading, error: loadError } = useApi<SettingsType>(
    () => fetchSettings(),
    [],
  );

  const [form, setForm] = useState<SettingsType>({
    wasabi_cost_per_tb: 0,
    sales_tax_rate: 0,
    discrepancy_threshold_pct: 0,
    low_disk_threshold_pct: 0,
    deleted_ratio_threshold: 0,
  });
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Initialize form when settings load
  useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const handleChange = useCallback(
    (key: keyof SettingsType) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      setForm((prev) => ({ ...prev, [key]: isNaN(value) ? 0 : value }));
    },
    [],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await updateSettings(form);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSaveError(err.message);
      } else {
        setSaveError("Failed to save settings");
      }
    } finally {
      setSaving(false);
    }
  }, [form]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" message="Loading settings..." />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-2">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-lg font-medium text-gray-400">Failed to load settings</p>
        <p className="text-sm text-gray-500">{loadError}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Configure audit thresholds and cost parameters
        </p>
      </div>

      {/* Success message */}
      {saveSuccess && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30
                        bg-emerald-500/10 px-4 py-3">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          <p className="text-sm font-medium text-emerald-500">
            Settings saved successfully!
          </p>
        </div>
      )}

      {/* Error message */}
      {saveError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30
                        bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <p className="text-sm font-medium text-red-500">{saveError}</p>
        </div>
      )}

      {/* Form */}
      <Card>
        <div className="grid gap-6 sm:grid-cols-2">
          <SettingField
            label="Wasabi Cost per TB ($)"
            description="Monthly cost per terabyte of Wasabi storage"
            value={form.wasabi_cost_per_tb}
            onChange={handleChange("wasabi_cost_per_tb")}
            step="0.01"
            min="0"
            prefix="$"
          />
          <SettingField
            label="Sales Tax Rate (%)"
            description="Tax rate applied to storage costs"
            value={form.sales_tax_rate}
            onChange={handleChange("sales_tax_rate")}
            step="0.01"
            min="0"
            max="100"
            suffix="%"
          />
          <SettingField
            label="Discrepancy Threshold (%)"
            description="Alert when Veeam vs Wasabi difference exceeds this"
            value={form.discrepancy_threshold_pct}
            onChange={handleChange("discrepancy_threshold_pct")}
            step="0.1"
            min="0"
            max="100"
            suffix="%"
          />
          <SettingField
            label="Low Disk Threshold (%)"
            description="Alert when BDR free disk space falls below this"
            value={form.low_disk_threshold_pct}
            onChange={handleChange("low_disk_threshold_pct")}
            step="0.1"
            min="0"
            max="100"
            suffix="%"
          />
          <SettingField
            label="Deleted Ratio Threshold"
            description="Alert when deleted-to-active storage ratio exceeds this"
            value={form.deleted_ratio_threshold}
            onChange={handleChange("deleted_ratio_threshold")}
            step="0.01"
            min="0"
          />
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={handleSave}
            className="btn-primary"
            disabled={saving}
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Saving...
              </span>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Settings
              </>
            )}
          </button>
        </div>
      </Card>

      {/* Pipeline Management */}
      <PipelineCard />
    </div>
  );
}

function PipelineCard() {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const status = await fetchPipelineStatus();
      setPipelineStatus(status);
      return status;
    } catch {
      return null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  // Poll while running
  useEffect(() => {
    if (pipelineStatus?.status === "running") {
      pollRef.current = setInterval(loadStatus, 5000);
    } else if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pipelineStatus?.status, loadStatus]);

  const handleTrigger = async () => {
    setTriggering(true);
    setTriggerError(null);
    try {
      await triggerPipeline();
      // Refresh status to show "running"
      await loadStatus();
    } catch (err: unknown) {
      if (err instanceof Error && "response" in err) {
        const axiosErr = err as { response?: { status: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 409) {
          setTriggerError("Pipeline is already running");
        } else {
          setTriggerError(axiosErr.response?.data?.detail || "Failed to start pipeline");
        }
      } else {
        setTriggerError("Failed to start pipeline");
      }
    } finally {
      setTriggering(false);
    }
  };

  const isRunning = pipelineStatus?.status === "running";

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString();
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "completed": return "text-emerald-400";
      case "running": return "text-blue-400";
      case "failed": return "text-red-400";
      default: return "text-gray-400";
    }
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Data Pipeline</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Runs daily at 7:00 AM MT. Trigger a manual run below.
          </p>
        </div>
        <button
          onClick={handleTrigger}
          disabled={triggering || isRunning}
          className="btn-primary"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Running...
            </span>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Pipeline Now
            </>
          )}
        </button>
      </div>

      {triggerError && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30
                        bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <p className="text-sm font-medium text-red-500">{triggerError}</p>
        </div>
      )}

      {pipelineStatus && pipelineStatus.status !== "no_runs" && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Last Run</h3>
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Status</dt>
              <dd className={`font-medium capitalize ${statusColor(pipelineStatus.status)}`}>
                {pipelineStatus.status}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Started</dt>
              <dd className="text-gray-900 dark:text-white">
                {formatDate(pipelineStatus.started_at)}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Completed</dt>
              <dd className="text-gray-900 dark:text-white">
                {formatDate(pipelineStatus.completed_at)}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </Card>
  );
}

interface SettingFieldProps {
  label: string;
  description: string;
  value: number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  step?: string;
  min?: string;
  max?: string;
  prefix?: string;
  suffix?: string;
}

function SettingField({
  label,
  description,
  value,
  onChange,
  step,
  min,
  max,
  prefix,
  suffix,
}: SettingFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
      <div className="relative mt-2">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
            {prefix}
          </span>
        )}
        <input
          type="number"
          value={value}
          onChange={onChange}
          step={step}
          min={min}
          max={max}
          className={`input-field ${prefix ? "pl-7" : ""} ${suffix ? "pr-8" : ""}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

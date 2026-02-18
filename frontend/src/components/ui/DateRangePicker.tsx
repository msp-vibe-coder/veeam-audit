import { useState } from "react";
import { Calendar } from "lucide-react";

interface DateRangePickerProps {
  dateFrom?: string;
  dateTo?: string;
  onApply: (dateFrom: string, dateTo: string) => void;
}

export default function DateRangePicker({
  dateFrom: initialFrom = "",
  dateTo: initialTo = "",
  onApply,
}: DateRangePickerProps) {
  const [from, setFrom] = useState(initialFrom);
  const [to, setTo] = useState(initialTo);

  function handleApply() {
    if (from && to) {
      onApply(from, to);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-gray-400" />
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="input-field w-40"
          placeholder="From"
        />
      </div>
      <span className="text-gray-400">to</span>
      <input
        type="date"
        value={to}
        onChange={(e) => setTo(e.target.value)}
        className="input-field w-40"
        placeholder="To"
      />
      <button onClick={handleApply} className="btn-primary" disabled={!from || !to}>
        Apply
      </button>
    </div>
  );
}

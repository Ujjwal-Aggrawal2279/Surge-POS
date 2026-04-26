import { LayoutDashboard, MonitorCheck } from "lucide-react";

interface Props {
  userFullName: string;
  onSelectDashboard: () => void;
  onSelectPOS: () => void;
}

export function HomeSelector({ userFullName, onSelectDashboard, onSelectPOS }: Props) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F6F8] px-4">
      <div className="w-full max-w-lg">
        <div className="mb-10 text-center">
          <div className="mb-3 flex items-center justify-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6938EF]">
              <span className="text-lg font-black text-white">S</span>
            </div>
            <span className="text-2xl font-black text-[#212B36]">Surge POS</span>
          </div>
          <p className="text-sm text-[#919EAB]">Welcome back, {userFullName}</p>
        </div>

        <p className="mb-4 text-center text-xs font-semibold uppercase tracking-widest text-[#919EAB]">
          Where would you like to go?
        </p>

        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={onSelectDashboard}
            className="group flex flex-col items-center gap-4 rounded-2xl border-2 border-[#6938EF]/20 bg-white px-6 py-8 shadow-sm transition-all hover:border-[#6938EF] hover:shadow-md active:scale-[0.98]"
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F4F3FF] transition-colors group-hover:bg-[#6938EF]">
              <LayoutDashboard className="h-8 w-8 text-[#6938EF] transition-colors group-hover:text-white" />
            </div>
            <div className="text-center">
              <p className="text-sm font-bold text-[#212B36]">Manager Dashboard</p>
              <p className="mt-0.5 text-xs text-[#919EAB]">Analytics &amp; inventory</p>
            </div>
          </button>

          <button
            type="button"
            onClick={onSelectPOS}
            className="group flex flex-col items-center gap-4 rounded-2xl border-2 border-[#0E9384]/20 bg-white px-6 py-8 shadow-sm transition-all hover:border-[#0E9384] hover:shadow-md active:scale-[0.98]"
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#E6FBF8] transition-colors group-hover:bg-[#0E9384]">
              <MonitorCheck className="h-8 w-8 text-[#0E9384] transition-colors group-hover:text-white" />
            </div>
            <div className="text-center">
              <p className="text-sm font-bold text-[#212B36]">POS Terminal</p>
              <p className="mt-0.5 text-xs text-[#919EAB]">Cashier sell screen</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}

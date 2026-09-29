import { RedirectIfAuthenticated } from "@/components/auth-guard";
import { Brand } from "@/components/brand";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="mb-8">
        <Brand />
      </div>
      <div className="w-full max-w-md rounded-xl border border-line bg-surface p-8 shadow-sm">
        <RedirectIfAuthenticated>{children}</RedirectIfAuthenticated>
      </div>
    </main>
  );
}

import { AppHeader } from "@/components/app-header";
import { RequireAuth } from "@/components/auth-guard";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <RequireAuth>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 lg:px-8">{children}</main>
    </RequireAuth>
  );
}

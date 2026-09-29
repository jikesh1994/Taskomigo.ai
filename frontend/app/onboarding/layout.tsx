import { RequireAuth } from "@/components/auth-guard";
import { Brand } from "@/components/brand";
import { SignOutButton } from "@/components/sign-out-button";

export default function OnboardingLayout({ children }: LayoutProps<"/onboarding">) {
  return (
    <RequireAuth>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 lg:px-8">
          <Brand href="/dashboard" />
          <SignOutButton />
        </div>
      </header>
      <main className="flex flex-1 flex-col">{children}</main>
    </RequireAuth>
  );
}

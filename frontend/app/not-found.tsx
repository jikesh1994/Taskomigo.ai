import { LinkButton } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <p className="text-sm font-medium text-primary">404</p>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-muted">The page you’re looking for doesn’t exist.</p>
      <LinkButton href="/" variant="secondary">
        Go home
      </LinkButton>
    </main>
  );
}

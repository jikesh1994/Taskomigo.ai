"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/services/errors";

/** Loading and error states for a query; renders `children(data)` once loaded. */
export function QueryState<T>({
  query,
  children,
}: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) {
    return (
      <div className="flex justify-center py-10 text-muted">
        <Spinner className="size-5" label="Loading" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <Alert tone="danger" title="Couldn't load this section">
        <p>{describeError(query.error)}</p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={() => query.refetch()}>
          Try again
        </Button>
      </Alert>
    );
  }
  return <>{children(query.data)}</>;
}

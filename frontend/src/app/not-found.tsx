import { SearchX } from "lucide-react";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/data/empty-state";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-base p-6">
      <EmptyState
        icon={SearchX}
        title="Page not found"
        description="The page or symbol you were looking for is not available in this workspace."
        action={
          <ButtonLink href="/dashboard" variant="primary" size="sm">
            Back to dashboard
          </ButtonLink>
        }
      />
    </div>
  );
}

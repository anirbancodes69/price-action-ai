import { SearchX } from "lucide-react";
import { ButtonLink } from "@/components/ui/button";
import { Empty } from "@/components/data/empty";

/** Refused / missing page (design-standards §11): say what is missing and where to go instead. */
export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-6">
      <div data-slot="card" className="w-full max-w-md rounded-xl border bg-card">
        <Empty
          icon={SearchX}
          title="Page not found"
          description="The page or symbol you were looking for is not available in this workspace."
          action={
            <ButtonLink href="/dashboard" variant="primary">
              Back to dashboard
            </ButtonLink>
          }
        />
      </div>
    </main>
  );
}

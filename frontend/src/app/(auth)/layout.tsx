import { AuthShowcase } from "@/features/auth/auth-showcase";
import { Brand } from "@/components/layout/brand";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="grid min-h-dvh bg-background lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <AuthShowcase />
      <div className="flex flex-col">
        <div className="flex h-16 items-center px-6 lg:hidden">
          <Brand href="/login" />
        </div>
        <main className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <div className="w-full max-w-[400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

import CustomDashboard from "@/components/CustomDashboard";
import { PageLayout } from "@/components";
import { DashboardProvider } from "@/hooks/useDashboard";

export default function Dashboard() {
  return (
    <DashboardProvider>
      <PageLayout>
        <CustomDashboard />
      </PageLayout>
    </DashboardProvider>
  );
}

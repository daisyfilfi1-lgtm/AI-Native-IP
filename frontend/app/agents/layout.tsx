import { CreatorIpProvider } from '@/contexts/CreatorIpContext';

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <CreatorIpProvider>{children}</CreatorIpProvider>;
}

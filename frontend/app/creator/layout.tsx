import { CreatorIpProvider } from '@/contexts/CreatorIpContext';

export default function CreatorLayoutRoot({
  children,
}: {
  children: React.ReactNode;
}) {
  return <CreatorIpProvider>{children}</CreatorIpProvider>;
}

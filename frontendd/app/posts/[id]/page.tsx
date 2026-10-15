import Shell from "@/components/shell";
import { PostDetail } from "@/components/posts";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Shell>
      <PostDetail id={id} />
    </Shell>
  );
}

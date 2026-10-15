import Shell from "@/components/shell";
import { PostComposer } from "@/components/posts";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Shell>
      <PostComposer id={id} />
    </Shell>
  );
}

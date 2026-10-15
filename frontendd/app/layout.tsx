import type { Metadata } from "next";
import Providers from "@/components/providers";
import "./globals.css";
export const metadata: Metadata = {
  title: "OrderHub — Facebook ажлын орчин",
  description: "Нийтлэл, сэтгэгдэл, Messenger мессежээ нэг дор удирдах",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="mn">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

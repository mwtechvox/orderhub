import type { Metadata } from "next";
import Providers from "@/components/providers";
import "./globals.css";
export const metadata: Metadata = {
  title: "OrderHub — Харилцагч бүртэйгээ илүү ойр",
  description: "Facebook нийтлэл, сэтгэгдэл, Messenger мессежээ нэг дор удирдах ажлын орчин.",
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

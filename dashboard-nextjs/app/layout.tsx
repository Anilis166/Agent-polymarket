import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Polymarket Bot Dashboard",
  description: "5-minute crypto prediction bot monitor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

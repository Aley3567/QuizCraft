import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuizCraft",
  description: "上传课件 PDF，自动出选择题，错题反馈引用课件原文",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

import "./styles.css";

export const metadata = {
  title: "Transcript AI | TCF Canada",
  description: "TCF Canada listening and language practice",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}


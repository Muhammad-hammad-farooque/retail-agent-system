// A template re-mounts on every navigation, which gives each page a smooth
// entrance transition without touching the pages themselves.
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="animate-page">{children}</div>;
}

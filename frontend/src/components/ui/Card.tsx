import clsx from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export default function Card({ children, className, padding = true }: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-xl border border-gray-200 bg-white shadow-sm",
        "dark:border-gray-700/50 dark:bg-gray-800/50",
        padding && "p-6",
        className,
      )}
    >
      {children}
    </div>
  );
}

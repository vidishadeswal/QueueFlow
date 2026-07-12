import WheelColumn from "./WheelColumn";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function daysInMonth(year: number, monthIndex: number): number {
  return new Date(year, monthIndex + 1, 0).getDate();
}

export default function DateTimeWheelPicker({
  value,
  onChange,
}: {
  value: Date;
  onChange: (updater: (prev: Date) => Date) => void;
}) {
  const year = value.getFullYear();
  const monthIndex = value.getMonth();
  const day = value.getDate();
  const hour24 = value.getHours();
  const minute = value.getMinutes();
  const period: "AM" | "PM" = hour24 >= 12 ? "PM" : "AM";
  const hour12 = ((hour24 + 11) % 12) + 1;

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 8 }, (_, i) => currentYear - 1 + i);
  const days = Array.from({ length: daysInMonth(year, monthIndex) }, (_, i) => i + 1);
  const hours = Array.from({ length: 12 }, (_, i) => i + 1);
  const minutes = Array.from({ length: 60 }, (_, i) => i);

  function update(next: Partial<{ year: number; monthIndex: number; day: number; hour12: number; minute: number; period: "AM" | "PM" }>) {
    onChange((prev) => {
      const prevHour24 = prev.getHours();
      const prevPeriod: "AM" | "PM" = prevHour24 >= 12 ? "PM" : "AM";
      const prevHour12 = ((prevHour24 + 11) % 12) + 1;

      const y = next.year ?? prev.getFullYear();
      const m = next.monthIndex ?? prev.getMonth();
      const maxDay = daysInMonth(y, m);
      const d = Math.min(next.day ?? prev.getDate(), maxDay);
      const h12 = next.hour12 ?? prevHour12;
      const min = next.minute ?? prev.getMinutes();
      const per = next.period ?? prevPeriod;

      let h24 = h12 % 12;
      if (per === "PM") h24 += 12;

      return new Date(y, m, d, h24, min, 0, 0);
    });
  }

  return (
    <div className="wheel-picker">
      <WheelColumn options={MONTHS} index={monthIndex} onChange={(i) => update({ monthIndex: i })} />
      <WheelColumn options={days.map(String)} index={day - 1} onChange={(i) => update({ day: i + 1 })} />
      <WheelColumn options={years.map(String)} index={years.indexOf(year)} onChange={(i) => update({ year: years[i] })} />
      <div className="wheel-divider" aria-hidden="true">
        :
      </div>
      <WheelColumn options={hours.map(String)} index={hour12 - 1} onChange={(i) => update({ hour12: hours[i] })} />
      <WheelColumn
        options={minutes.map((m) => String(m).padStart(2, "0"))}
        index={minute}
        onChange={(i) => update({ minute: i })}
      />
      <WheelColumn options={["AM", "PM"]} index={period === "AM" ? 0 : 1} onChange={(i) => update({ period: i === 0 ? "AM" : "PM" })} />
    </div>
  );
}

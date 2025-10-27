# StatCard Component

A reusable component for displaying key metrics and statistics with icons and trend indicators.

## Usage

```tsx
import StatCard from '@/components/StatCard';
import { Activity } from 'lucide-react';

function Dashboard() {
  return (
    <StatCard
      title="Total Events"
      value={1234}
      icon={Activity}
      trend={{ value: "12%", isPositive: true }}
      color="blue"
    />
  );
}
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | `string` | Yes | - | The title/label for the metric |
| `value` | `string \| number` | Yes | - | The numeric value to display |
| `icon` | `LucideIcon` | Yes | - | Lucide icon component to display |
| `trend` | `object` | No | - | Trend information object |
| `trend.value` | `string` | Yes* | - | Trend percentage or value |
| `trend.isPositive` | `boolean` | Yes* | - | Whether the trend is positive |
| `color` | `"blue" \| "red" \| "green" \| "yellow"` | No | `"blue"` | Color theme for the card |

## Color Themes

- **blue**: Blue gradient with blue accents (default)
- **red**: Red gradient with red accents
- **green**: Green gradient with green accents
- **yellow**: Yellow gradient with yellow accents

## Examples

### Basic Usage
```tsx
<StatCard
  title="Active Threats"
  value={42}
  icon={Shield}
/>
```

### With Trend
```tsx
<StatCard
  title="Blocked IPs"
  value={156}
  icon={Ban}
  trend={{ value: "8%", isPositive: true }}
  color="green"
/>
```

### Different Colors
```tsx
<StatCard title="Errors" value={3} icon={AlertTriangle} color="red" />
<StatCard title="Success Rate" value="99.9%" icon={CheckCircle} color="green" />
```

## Styling

The component uses Tailwind CSS classes and includes:
- Gradient backgrounds based on color theme
- Glow effects for visual appeal
- Responsive design
- Hover animations

## Accessibility

- Icons are decorative and include `aria-hidden="true"`
- Values are properly formatted with `toLocaleString()`
- Color contrast meets WCAG guidelines

## Testing

The component includes comprehensive unit tests covering:
- Rendering with all prop combinations
- Trend indicator display
- Color theme application
- Number formatting

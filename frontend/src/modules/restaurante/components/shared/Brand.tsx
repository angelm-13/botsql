import type { Translations } from '../../i18n/translations'

export function FlameMark({ size = 44 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M52 10 C40 25 33 38 40 51 C44 58 54 61 54 61 C54 61 63 58 66 51 C71 39 63 27 52 10Z" fill="var(--brand-primary)" />
    <path d="M70 24 C61 34 57 44 61 53 C63 58 71 61 71 61 C71 61 79 58 81 53 C85 45 80 36 70 24Z" fill="var(--brand-primary)" />
    <ellipse cx="60" cy="79" rx="41" ry="9" fill="var(--brand-dark)" />
  </svg>
}

export function LogoDivider({ width = 130 }: { width?: number }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 7, width }}>
    <span style={{ flex: 1, height: 1, background: 'var(--brand-primary)' }} />
    <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--brand-primary)', flexShrink: 0 }} />
    <span style={{ flex: 1, height: 1, background: 'var(--brand-primary)' }} />
  </div>
}

interface RestaurantLogoProps {
  t?: Translations
  size?: number
  showText?: boolean
}

export function RestaurantLogo({ t, size = 44, showText = true }: RestaurantLogoProps) {
  /* Version horizontal: icono a la izquierda, tagline arriba del wordmark y
     linea divisoria abajo. Solo se usa en la barra superior (siempre oscura,
     ver .topbar en app.css), por eso el texto va en blanco fijo en vez de
     var(--text)/var(--muted) (esos tokens son para texto sobre fondo claro). */
  return <div className="restaurant-logo" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
    <FlameMark size={size} />
    {showText && <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontFamily: 'var(--font-body)', fontWeight: 600, fontSize: Math.max(size * 0.19, 9), letterSpacing: '1.4px', color: 'rgba(255,255,255,.7)', textTransform: 'uppercase', lineHeight: 1 }}>
        {t ? t.tagline : 'Tu plantilla de restaurante'}
      </span>
      <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: size * 0.46, letterSpacing: '1px', color: '#fff', lineHeight: 1 }}>
        {t ? t.welcome : 'MI RESTAURANTE'}
      </span>
      <LogoDivider width={size * 2.5} />
    </div>}
  </div>
}

export function RestaurantLogoStacked({ t, size = 84 }: { t?: Translations; size?: number }) {
  /* Version vertical: icono grande arriba, wordmark, linea con punto y tagline abajo. Para el login. */
  return <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
    <FlameMark size={size} />
    <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: size * 0.4, letterSpacing: '2px', color: 'var(--text)', lineHeight: 1 }}>
      {t ? t.welcome : 'MI RESTAURANTE'}
    </span>
    <LogoDivider width={size * 1.9} />
    <span style={{ fontFamily: 'var(--font-body)', fontWeight: 600, fontSize: Math.max(size * 0.16, 11), letterSpacing: '2px', color: 'var(--muted)', textTransform: 'uppercase' }}>
      {t ? t.tagline : 'Tu plantilla de restaurante'}
    </span>
  </div>
}

import { useEffect, useRef, useState } from 'react'

interface AnimatedNumberProps {
  value: number | string | null | undefined
  decimals?: number
  format?: (n: number) => string
}

/**
 * Muestra un numero que "cuenta" suavemente hacia su valor real cada vez que
 * cambia (en vez de saltar de golpe), usando requestAnimationFrame con una
 * curva de desaceleracion. `format` recibe el valor intermedio (ya
 * redondeado a `decimals`) y decide como se ve (por ejemplo money() para
 * montos). Puramente cosmetico: no afecta ningun calculo ni dato real.
 */
export function AnimatedNumber({ value, decimals = 0, format }: AnimatedNumberProps) {
  const numericValue = Number(value) || 0
  const [display, setDisplay] = useState(numericValue)
  const fromRef = useRef(numericValue)
  useEffect(() => {
    const from = fromRef.current
    const to = numericValue
    if (from === to) return
    const duration = 550
    const start = performance.now()
    let raf: number
    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      const current = from + (to - from) * eased
      setDisplay(current)
      if (progress < 1) raf = requestAnimationFrame(tick)
      else fromRef.current = to
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [numericValue])
  const rounded = Number(display.toFixed(decimals))
  return <>{format ? format(rounded) : rounded}</>
}

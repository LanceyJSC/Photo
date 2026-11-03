import React, { useEffect, useState } from 'react';
import { View, StyleSheet } from 'react-native';

const COLS = 20, ROWS = 12;
// TV snow: a grid of random grey cells that reshuffles ~15x/second while mounted.
export function Static() {
  const [, setSeed] = useState(0);
  useEffect(() => { const t = setInterval(() => setSeed(s => s + 1), 70); return () => clearInterval(t); }, []);
  const cells = [];
  for (let i = 0; i < COLS * ROWS; i++) {
    const v = (Math.random() * 255) | 0;
    cells.push(<View key={i} style={{ width: `${100 / COLS}%`, height: `${100 / ROWS}%`, backgroundColor: `rgb(${v},${v},${v})` }} />);
  }
  return <View pointerEvents="none" style={[StyleSheet.absoluteFill, { flexDirection: 'row', flexWrap: 'wrap' }]}>{cells}</View>;
}

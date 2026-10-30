// White noise has to start inside the click that asked for it.
// Each window has its own AudioContext. localStorage tells the other one to stop
// so the main window and the tomato never play at the same time.

const KIND_KEY = 'wv-focus-noise'
const OWNER_KEY = 'wv-focus-noise-owner'

let ctx = null
let nodes = []

function ownerId() {
  return new URLSearchParams(window.location.search).get('surface') === 'pet' ? 'pet' : 'main'
}

export function noiseKind() {
  const saved = window.localStorage.getItem(KIND_KEY)
  if (saved === 'rain' || saved === 'cafe' || saved === 'tone' || saved === 'off') {
    return saved
  }
  return 'rain'
}

export function rememberNoiseKind(kind) {
  window.localStorage.setItem(KIND_KEY, kind)
}

export function unlockNoise() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) {
    return null
  }
  if (!ctx) {
    ctx = new Ctx()
  }
  const silent = ctx.createBuffer(1, 1, ctx.sampleRate)
  const tap = ctx.createBufferSource()
  tap.buffer = silent
  tap.connect(ctx.destination)
  tap.start()
  ctx.resume()
  return ctx
}

function stopNodes() {
  nodes.forEach((node) => {
    try {
      node.stop?.()
    } catch {
      // already stopped
    }
    try {
      node.disconnect?.()
    } catch {
      // already disconnected
    }
  })
  nodes = []
}

export function stopNoise() {
  stopNodes()
  if (window.localStorage.getItem(OWNER_KEY) === ownerId()) {
    window.localStorage.setItem(OWNER_KEY, '')
  }
}

export function startNoise(kind = noiseKind()) {
  stopNodes()
  if (kind === 'off') {
    return
  }
  if (!unlockNoise()) {
    return
  }
  const gain = ctx.createGain()
  gain.gain.value = kind === 'tone' ? 0.08 : 0.16
  gain.connect(ctx.destination)
  nodes.push(gain)
  if (kind === 'tone') {
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.value = 196
    osc.connect(gain)
    osc.start()
    nodes.push(osc)
  } else {
    const length = ctx.sampleRate * 2
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
    const data = buffer.getChannelData(0)
    for (let index = 0; index < length; index += 1) {
      data[index] = Math.random() * 2 - 1
    }
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.loop = true
    const filter = ctx.createBiquadFilter()
    filter.type = kind === 'rain' ? 'highpass' : 'lowpass'
    filter.frequency.value = kind === 'rain' ? 900 : 420
    source.connect(filter).connect(gain)
    source.start()
    nodes.push(source, filter)
  }
  ctx.resume()
  window.localStorage.setItem(OWNER_KEY, ownerId())
}

// Call this synchronously from the click handler, before any await.
export function claimNoise(kind = noiseKind()) {
  unlockNoise()
  startNoise(kind)
}

window.addEventListener('storage', (event) => {
  if (event.key === OWNER_KEY && event.newValue !== ownerId()) {
    stopNodes()
  }
})

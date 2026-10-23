// Offline-render notes through Logic/GarageBand .exs instruments with AVAudioUnitSampler.
// usage: render <score.json> <out.wav>
// score: {"instrument": "/path.exs", "seconds": 4, "notes": [[start_s, midi, dur_s, velocity], ...]}
import AVFoundation

let args = CommandLine.arguments
let score = try! JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[1]))) as! [String: Any]
let notes = (score["notes"] as! [[Double]]).sorted { $0[0] < $1[0] }
let seconds = score["seconds"] as! Double

let engine = AVAudioEngine()
let format = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)!
_ = engine.mainMixerNode
engine.stop()
try! engine.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 512)
let sampler = AVAudioUnitSampler()
engine.attach(sampler)
engine.connect(sampler, to: engine.mainMixerNode, format: format)
try! sampler.loadInstrument(at: URL(fileURLWithPath: score["instrument"] as! String))
try! engine.start()

let out = try! AVAudioFile(forWriting: URL(fileURLWithPath: args[2]), settings: [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 44100, AVNumberOfChannelsKey: 2, AVLinearPCMBitDepthKey: 32, AVLinearPCMIsFloatKey: true], commonFormat: .pcmFormatFloat32, interleaved: false)
let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 512)!
var events: [(Double, UInt8, UInt8, Bool)] = []
for n in notes {
    events.append((n[0], UInt8(n[1]), UInt8(n[3]), true))
    events.append((n[0] + n[2], UInt8(n[1]), 0, false))
}
events.sort { $0.0 < $1.0 }
var i = 0
let total = AVAudioFramePosition(seconds * 44100)
while engine.manualRenderingSampleTime < total {
    let now = Double(engine.manualRenderingSampleTime) / 44100
    while i < events.count && events[i].0 <= now {
        let e = events[i]
        if e.3 { sampler.startNote(e.1, withVelocity: e.2, onChannel: 0) } else { sampler.stopNote(e.1, onChannel: 0) }
        i += 1
    }
    let status = try! engine.renderOffline(512, to: buf)
    if status == .success { try! out.write(from: buf) }
}

local dfpwm = require("cc.audio.dfpwm")
local decode = dfpwm.make_decoder()

local speaker = peripheral.find("speaker")
if not speaker then
    error("No speaker found")
end

local ws = assert(http.websocket("ws://<HOST_IP>:<PORT>"))

function play_audio(data, volume)
    local buffer = decode(data)
    for i = 1, #buffer do
        buffer[i] = buffer[i] * volume
    end

    while not speaker.playAudio(buffer) do
        os.pullEvent("speaker_audio_empty")
    end
end

print("Waiting for audio data...")
while true do
    ws.send("more")
    local data = ws.receive()
    print("Received audio data")
    play_audio(data, 1.0)
end
-- Unreachable but whatever
ws.close()

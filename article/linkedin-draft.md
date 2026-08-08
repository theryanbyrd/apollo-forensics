# How to Fake a Moon Landing

The year was 1969, and America's politicians and scientists were in a panic. The Soviet Union, the rival we'd been locked in a Cold War with since the 1940s, had been winning space for a decade: first satellite (Sputnik, 1957), first animal in orbit (RIP, Laika), and in April 1961 the first human, cosmonaut Yuri Gagarin, who circled the Earth ten months before American John Glenn did. Americans were winners who kept losing. So President Kennedy made a bet with a deadline: a man on the Moon before the decade was out.

And, if you believe the official narrative, Apollo 11 delivered with five months to spare. Neil Armstrong and Buzz Aldrin landed on the Moon on July 20, 1969, at 20:17 UTC. "The Eagle has landed."

But did we really? If so, kindly explain why the flag is waving on a Moon with no atmosphere. Help me understand how humans flew through the Van Allen radiation belts without dying. And those shadows in NASA's photos point every which way. Nice try, fakers.

Last weekend I became obsessed with a strange assignment: take the twelve moon-landing hoax claims that can be tested purely in software, write real code for each one, run it on real public data, and let the results land wherever they land.

One rule made it interesting: every test had to be falsifiable. (Falsifiable means it can be proven wrong by an observation or experiment.) Before running anything, each experiment declared the result that would have supported the hoax. Shadow lines converging below the horizon? Studio lamp. A feather falling on an air-drag curve? Sound stage. A radio delay of zero seconds? Houston, we have a soundstage. A test that can't fail isn't a test; it's a pep rally.

Twelve claims went in. Twelve pre-registered ways for the conspiracy to win. Can you guess the scorecard?

A few favorites:

**You can hear the Moon answer back**

During the Apollo 11 moonwalk, CapCom's voice went up to the Moon, leaked through the astronauts' headsets into their live microphones, and came back down. Which means the Houston control-room tapes should contain his own voice returning about 2.6 seconds after he speaks: the Earth-Moon round trip at the speed of light.

I pulled three reels of NASA control-room audio from archive.org and cross-correlated. The echo is there: 2.644 ± 0.035 seconds, a 5-sigma detection across 43 transmissions, sitting right on JPL's predicted light-time curve for that exact hour. The landing tape, recorded before the leak-prone moonwalk audio configuration, correctly shows no echo. The physics ran its own control group.

There's an 11-second clip in the repo where you can literally listen to a sentence bounce off the Moon. Nothing in 1969 could fake a distance-correct, ephemeris-tracking delay across hundreds of hours of live conversation. Radio doesn't lie about distance.

**I didn't argue about the computer. I ran it.**

"1960s computers were too weak to fly to the Moon." Fine. The Apollo 11 Lunar Module source code is public, transcribed from the original July 1969 program listing. I reassembled it with a modern build of the period assembler and got a binary that is byte-for-byte identical to an independent transcription of the flown rope memory. All 36 bank checksums pass.

Then I booted it on a cycle-accurate emulator. It runs, in real time, at the authentic 85,000 cycles per second, doing exactly what it did on the pad: autopilot housekeeping at 10 Hz and the telemetry downlink every 2 seconds. Cost on a modern laptop: about 4% of one core and one megabyte of RAM. The entire flight program is 67 KB. The chart I made about the program is bigger than the program.

Bonus: the famous 1201/1202 landing alarms are right there in the source, a priority-scheduled operating system shedding low-priority work under overload, exactly as designed. The "primitive" computer had a better degradation story than most microservices I've reviewed.

**The feather is the whole case**

"It's Earth footage slowed down 2.46x." This one is sneaky, because a single falling object filmed in slow motion really can imitate lunar gravity. The math checks out. So the test has to be a joint one, and that's where it dies.

I tracked the Apollo 15 hammer-and-feather drop frame by frame. The feather accelerates all the way down and lands with the hammer. In air, at any playback speed, a falcon feather tops out around walking pace; slow the film and you slow the feather too. The observed feather hits about 4x faster than air physics allows. And if the footage were really slowed 2.46x, David Scott's synced audio means the real man was speaking at 9.9 syllables per second. Try that sentence out loud at triple speed and report back.

**Japan checked NASA's homework, 37 years later**

In 2008, Japan's Kaguya orbiter mapped the Moon's terrain with its own stereo cameras. I rendered the horizon a camera should see from the Apollo 15 landing site using only the Japanese elevation data, then overlaid it on the 1971 photographs. The predicted ridgeline rides the photographed skyline across the entire frame: 0.18 degrees RMS, correlation 0.998, at exactly the documented camera direction. A set painter in 1971 would have needed topographic data that wouldn't exist for four more decades.

**And finally, the math that eats the conspiracy alive**

The one quantitative model in the literature (Grimes, 2016, PLOS ONE) treats secrets as a leak process, calibrated on conspiracies that actually got exposed. I reproduced his published numbers, then ran the sensitivity analysis. A 411,000-person hoax has an expected lifespan of about 1.2 years. The largest team that plausibly stays silent for 57 years: about 49 people. The smallest team that could fabricate 382 kg of internally consistent moon rock, ephemeris-locked radio, and terrain matching future satellites: 870 and up. The conspiracy needs to be simultaneously tiny and enormous.

My favorite finding in the whole project: "they'd all be dead by now, someone would have confessed" is correct. In my simulations, deathbed confessions are the leading cause of conspiracy death. The silence is the evidence.

**The part I actually care about**

I didn't do months of research here. I described the twelve experiments, each with its falsification criterion, and set AI agents loose on the implementation: photogrammetry, audio signal processing, radiation transport, film forensics, an agent-based secrecy model, a flight-software build chain. All twelve pipelines ran in about a day, and each documented its data sources, its error bars, and its failures. (There were failures. One pipeline discovered mid-analysis that the hammer slides down a small mound after landing, and had to handle it. The Moon does not care about your code.)

That's the real story for me: falsifiable questions are now cheap. The gap between "someone should check that" and "checked, with error bars, here's the repo" used to be a grant proposal. Now it's a weekend.

Oh, and the scorecard? Hoax 0, Moon 12.

Everything is public and reproducible:

* The code and data: github.com/theryanbyrd/apollo-forensics
* The interactive site, including a live replay of Apollo 11 running on the real guidance computer's timeline, DSKY and all (try keying VERB 16 NOUN 65): apollo-forensics.vercel.app

The moon landing survived code review. Approved. Merging to history.

So, what should I put through review next? JFK? Area 51? Whether birds are real? Drop your favorite conspiracy below. If it can be tested in software, it can be tested in a weekend.

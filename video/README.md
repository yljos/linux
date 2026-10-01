# Cut from start time (-ss) to end time (-to) without re-encoding (Fast, keyframe accurate)
ffmpeg -ss 00:01:30 -to 00:02:45 -i input.mp4 -c copy output.mp4

# Cut from start time (-ss) for a specific duration (-t)
ffmpeg -ss 00:01:30 -t 00:01:15 -i input.mp4 -c copy output.mp4

# Frame-accurate cut (Slower, re-encodes video, keeps audio original)
ffmpeg -ss 00:01:30 -to 00:02:45 -i input.mp4 -c:v libx264 -crf 18 -c:a copy output.mp4

# Merge multiple video files
# 1. Create a list file (e.g., list.txt) containing:
# file 'part1.mp4'
# file 'part2.mp4'
# 2. Run the concat command
ffmpeg -f concat -safe 0 -i list.txt -c copy merged.mp4
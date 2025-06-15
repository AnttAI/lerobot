python -m lerobot.record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=white_follower_arm \
    --robot.cameras="{ head: {type: opencv, index_or_path: '/dev/video2', width: 640, height: 480, fps: 30}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=white_leader_arm \
    --display_data=true \
    --dataset.repo_id=AnttAI/record-test3 \
    --dataset.num_episodes=1 \
    --dataset.single_task="Pick the wooden block and put in the plate" \
    --dataset.episode_time_s=15 \
    --dataset.reset_time_s=15 \
    --resume=true 
    

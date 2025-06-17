python -m lerobot.record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=blue_follower_arm \
    --robot.cameras="{ head: {type: opencv, index_or_path: '/dev/video2', width: 640, height: 480, fps: 30}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=blue_leader_arm \
    --policy.path=/home/jony/Downloads/act_so101_test_new2/checkpoints/last/pretrained_model \
    --display_data=true \
    --dataset.push_to_hub=False \
    --dataset.repo_id=AnttAI/eval_record-test3_e2 \
    --dataset.num_episodes=1 \
    --dataset.single_task="Pick the wooden block and put in the plate" \
    --dataset.episode_time_s=30 \
    --dataset.reset_time_s=15 \
    --resume=true
    

import base64

import numpy as np

from tf_agents.trajectories import time_step as ts

from protobuf.message_pb2 import ProtoGameDetail

DEBUG = True

def log(msg):
    if DEBUG:
        print(msg)

def decode_protobuf(filename, prepare_fn=None):
    with open(filename) as protofile:
        msg_bytes = base64.b64decode(protofile.read())
        protobuf = ProtoGameDetail()
        protobuf.ParseFromString(msg_bytes)

        if prepare_fn:
            return prepare_fn(protobuf)
        return protobuf

def transform_protobuf(protobuf):
    """ Returns numpy corresponding to tf agents time_step properties"""

    log('transform_protobuf started')

    log('ClawOpen length is {}'.format(len(protobuf.ClawOpen)))
    log('BlockCount length is {}'.format(len(protobuf.BlockCount)))
    log('BlocksPosition length is {}'.format(len(protobuf.BlocksPosition)))
    log('CurrentBPScore length is {}'.format(len(protobuf.CurrentBPScore)))

    protobuf_len = len(protobuf.CurrentBPScore)
    max_blocks = protobuf.BlockCount[0]

    log('protobuf contains {} steps'.format(protobuf_len))
    log('max blocks value is {}'.format(max_blocks))

    log('block positions recieved {}'.format(len(protobuf.BlocksPosition)))

    block_positons = protobuf.BlocksPosition[:protobuf_len * max_blocks * 2]
    claw_positions = protobuf.ClawPosition[:protobuf_len * 2]
    rotation_global_claw_arm = protobuf.rotationGlobalClawArm[:protobuf_len * 3]
    rotation_claw_arm = protobuf.rotationClawArm[:protobuf_len * 3]
    block_count = protobuf.BlockCount[:protobuf_len]
    claw_cart_position = protobuf.ClawPosition[:protobuf_len]
    claw_cart_velocity = protobuf.ClawCartVelocity[:protobuf_len]
    claw_open = protobuf.ClawOpen[:protobuf_len]
    claw_facing_ground = protobuf.ClawFacingGround[:protobuf_len]
    current_bp_score = protobuf.CurrentBPScore[:protobuf_len]

    observations = [
        np.expand_dims(np.array(block_count, dtype=np.float32), axis=1),
        np.array(block_positons, dtype=np.float32).reshape(protobuf_len, max_blocks * 2),
        np.expand_dims(np.array(claw_cart_position, dtype=np.float32), axis=1),
        np.array(claw_positions, dtype=np.float32).reshape(protobuf_len, 2),
        np.array(rotation_global_claw_arm, dtype=np.float32).reshape(protobuf_len, 3),
        np.array(rotation_claw_arm, dtype=np.float32).reshape(protobuf_len, 3),
        np.expand_dims(np.array(claw_cart_velocity, dtype=np.float32), axis=1),
        np.expand_dims(np.array(claw_open, dtype=np.float32), axis=1),
        np.expand_dims(np.array(claw_facing_ground, dtype=np.float32), axis=1),
        np.expand_dims(np.array(current_bp_score, dtype=np.float32), axis=1),
        # np.expand_dims(np.array(protobuf.CurrentScore, dtype=np.int32), axis=1),
    ]
    observations = np.hstack(observations)

    actions = np.reshape(
        np.array(protobuf.PlayerControls, dtype=np.int32),
        (protobuf_len, 10))

    def get_step_types(score):
        nonlocal prev_score
        nonlocal prev_step_type

        if prev_step_type == ts.StepType.LAST or prev_step_type is None:
            return ts.StepType.FIRST
        step_type = ts.StepType.LAST if score > prev_score else ts.StepType.MID
        prev_score = score
        return step_type

    rewards = np.array(
        get_step_scores(current_bp_score),
        dtype=np.float32)
    prev_score = 0
    prev_step_type = None
    step_types = np.array(
        list(map(get_step_types, protobuf.CurrentScore)),
        dtype=np.int32)
    next_step_types = np.concatenate((step_types[1:], [ts.StepType.LAST]))
    log('step types len is {}'.format(len(step_types)))
    log('next step types len is {}'.format(len(next_step_types)))

    return {
        'actions': normalize_actions(actions),
        'observations': observations,
        'rewards': rewards,
        'step_types': step_types,
        'next_step_types': next_step_types,
    }

def get_step_scores(scores):
    """
    Return array where number at index represents
    a reward for step with the same index
    """
    step_scores = [scores[0]]
    last_score = scores[0]

    for score in scores:
        new_score = 0
        if last_score != score:
            new_score = score - step_scores[-1]
            last_score = score
        if new_score < 0:
            new_score = 0
        step_scores.append(new_score)

    return step_scores

def normalize_actions(actions):
    last_action = 0
    normalized_actions = []

    for action in actions:
        current_action = np.where(action == 1)[0]
        current_action = last_action if len(current_action) == 0 else current_action[0]
        last_action = 0 if current_action == 9 else current_action
        normalized_actions.append([current_action])

    return np.array(normalized_actions, dtype=np.int32)

if __name__ == '__main__':
    asd = decode_protobuf('protobuf/example3.b64', transform_protobuf)
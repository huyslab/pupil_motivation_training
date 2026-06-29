







import os
import csv
import json
import ctypes
import time
import random as py_random
import re
import shutil
import math


os.environ.pop('SDL_AUDIODRIVER', None)
os.environ.pop('SDL_AUDIO_DEVICE', None)

from psychopy import locale_setup
from psychopy import prefs

LAB_AUDIO_LATENCY_MODE = 1
LAB_AUDIO_SAMPLE_RATE_TARGET = 48000
LAB_AUDIO_SELECTED_DEVICE = ''
LAB_AUDIO_SELECTED_DEVICE_INDEX = None
LAB_AUDIO_SELECTED_HOST_API = ''
LAB_AUDIO_SELECTED_OUTPUT_CHANNELS = None
LAB_AUDIO_SELECTED_DEVICE_INFO = ''
LAB_AUDIO_SELECTED_DEVICE_DEFAULT_SAMPLE_RATE = None
LAB_AUDIO_STREAM_SAMPLE_RATE = None
LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX = None
LAB_AUDIO_STREAM_PREDICTED_LATENCY_S = None
LAB_AUDIO_STREAM_STATUS = ''
LAB_AUDIO_PREFLIGHT_PASSED = False
LAB_AUDIO_CONFIG_ERROR = ''
LAB_AUDIO_SPEAKER = None
LAB_AUDIO_PREFLIGHT_SOUND = None


def _ptb_device_value(device, *keys, default=None):
    for key in keys:
        if key in device:
            return device[key]
    return default


def _ptb_device_name(device):
    return str(_ptb_device_value(device, 'DeviceName', 'name', default=''))


def _ptb_device_api(device):
    return str(_ptb_device_value(device, 'HostAudioAPIName', 'hostapi', default=''))


def _ptb_device_index(device):
    value = _ptb_device_value(device, 'DeviceIndex', 'index', default=None)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ptb_device_output_channels(device):
    value = _ptb_device_value(device, 'NrOutputChannels', 'numOutputChannels', default=0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _ptb_device_default_sample_rate(device):
    value = _ptb_device_value(device, 'DefaultSampleRate', 'defaultSampleRate', default=None)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _describe_ptb_device(device):
    return (
        'api=%r | device=%r | index=%r | outputChannels=%r | defaultSampleRate=%r'
        % (
            _ptb_device_api(device),
            _ptb_device_name(device),
            _ptb_device_index(device),
            _ptb_device_output_channels(device),
            _ptb_device_default_sample_rate(device),
        )
    )


def _focusrite_device_rank(device):

    name = _ptb_device_name(device).lower()
    sample_rate = _ptb_device_default_sample_rate(device)
    return (
        0 if name.startswith('speakers') else 1,
        0 if 'focusrite usb audio' in name else 1,
        abs((sample_rate if sample_rate is not None else 0.0) - LAB_AUDIO_SAMPLE_RATE_TARGET),
        _ptb_device_index(device) if _ptb_device_index(device) is not None else 999999,
    )


def configure_ptb_wasapi_audio():

    global LAB_AUDIO_SELECTED_DEVICE, LAB_AUDIO_SELECTED_DEVICE_INDEX
    global LAB_AUDIO_SELECTED_HOST_API, LAB_AUDIO_SELECTED_OUTPUT_CHANNELS
    global LAB_AUDIO_SELECTED_DEVICE_INFO, LAB_AUDIO_SELECTED_DEVICE_DEFAULT_SAMPLE_RATE
    global LAB_AUDIO_CONFIG_ERROR

    LAB_AUDIO_SELECTED_DEVICE = ''
    LAB_AUDIO_SELECTED_DEVICE_INDEX = None
    LAB_AUDIO_SELECTED_HOST_API = ''
    LAB_AUDIO_SELECTED_OUTPUT_CHANNELS = None
    LAB_AUDIO_SELECTED_DEVICE_INFO = ''
    LAB_AUDIO_SELECTED_DEVICE_DEFAULT_SAMPLE_RATE = None
    LAB_AUDIO_CONFIG_ERROR = ''

    try:
        prefs.hardware['audioLib'] = ['PTB']



        prefs.hardware['audioLatencyMode'] = LAB_AUDIO_LATENCY_MODE
        prefs.hardware['audioWASAPIOnly'] = True
    except Exception as error:
        LAB_AUDIO_CONFIG_ERROR = 'Could not set PsychoPy PTB/WASAPI preferences: ' + repr(error)
        return

    requested_device = (
        os.environ.get('PSYCHOPY_AUDIO_DEVICE', '').strip()
        or os.environ.get('LAB_AUDIO_DEVICE', '').strip()
    )

    try:
        import psychtoolbox.audio as ptb_audio
        devices = ptb_audio.get_devices()
        output_devices = [device for device in devices if _ptb_device_output_channels(device) > 0]

        candidates = [
            device for device in output_devices
            if (
                'focusrite' in _ptb_device_name(device).lower()
                and 'wasapi' in _ptb_device_api(device).lower()
                and _ptb_device_output_channels(device) >= 2
                and _ptb_device_index(device) is not None
            )
        ]

        if requested_device:
            requested_lower = requested_device.lower()
            candidates = [
                device for device in candidates
                if requested_lower in (
                    _ptb_device_name(device) + ' ' + _ptb_device_api(device) + ' ' + str(_ptb_device_index(device))
                ).lower()
            ]

        if not candidates:
            visible_outputs = '; '.join(_describe_ptb_device(device) for device in output_devices) or 'none'
            if requested_device:
                prefix = 'Requested Focusrite device selector %r found no matching WASAPI output. ' % requested_device
            else:
                prefix = 'No Focusrite WASAPI stereo output device was found. '
            LAB_AUDIO_CONFIG_ERROR = prefix + 'Visible PTB output devices: ' + visible_outputs
            LAB_AUDIO_SELECTED_DEVICE_INFO = LAB_AUDIO_CONFIG_ERROR
            return

        selected = sorted(candidates, key=_focusrite_device_rank)[0]
        LAB_AUDIO_SELECTED_DEVICE = _ptb_device_name(selected)
        LAB_AUDIO_SELECTED_DEVICE_INDEX = _ptb_device_index(selected)
        LAB_AUDIO_SELECTED_HOST_API = _ptb_device_api(selected)
        LAB_AUDIO_SELECTED_OUTPUT_CHANNELS = _ptb_device_output_channels(selected)
        LAB_AUDIO_SELECTED_DEVICE_DEFAULT_SAMPLE_RATE = _ptb_device_default_sample_rate(selected)
        LAB_AUDIO_SELECTED_DEVICE_INFO = (
            'focusrite_wasapi_selected | '
            + _describe_ptb_device(selected)
            + ' | candidates=' + str(len(candidates))
            + ' | latencyClass=' + str(LAB_AUDIO_LATENCY_MODE)
        )


        prefs.hardware['audioDevice'] = [LAB_AUDIO_SELECTED_DEVICE]

    except Exception as error:
        LAB_AUDIO_CONFIG_ERROR = 'PTB device scan failed: ' + repr(error)
        LAB_AUDIO_SELECTED_DEVICE_INFO = LAB_AUDIO_CONFIG_ERROR
        return


def _record_shared_audio_stream_details(speaker):

    global LAB_AUDIO_STREAM_SAMPLE_RATE, LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX
    global LAB_AUDIO_STREAM_PREDICTED_LATENCY_S, LAB_AUDIO_STREAM_STATUS

    LAB_AUDIO_STREAM_SAMPLE_RATE = getattr(speaker, 'sampleRateHz', None)
    LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX = getattr(speaker, 'index', None)
    LAB_AUDIO_STREAM_PREDICTED_LATENCY_S = None

    try:
        status = speaker.stream.status
    except Exception:
        status = None

    if isinstance(status, dict):
        LAB_AUDIO_STREAM_SAMPLE_RATE = status.get('SampleRate', LAB_AUDIO_STREAM_SAMPLE_RATE)
        LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX = status.get(
            'OutDeviceIndex', LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX
        )
        LAB_AUDIO_STREAM_PREDICTED_LATENCY_S = status.get('PredictedLatency', None)

    LAB_AUDIO_STREAM_STATUS = (
        'shared_stream_open'
        + ' | selectedDevice=' + repr(getattr(speaker, 'name', LAB_AUDIO_SELECTED_DEVICE))
        + ' | selectedIndex=' + repr(LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX)
        + ' | hostAPI=' + repr(LAB_AUDIO_SELECTED_HOST_API)
        + ' | latencyMode=' + repr(LAB_AUDIO_LATENCY_MODE)
    )


def verify_ptb_wasapi_audio_configuration():

    global LAB_AUDIO_PREFLIGHT_PASSED, LAB_AUDIO_CONFIG_ERROR
    global LAB_AUDIO_SPEAKER, LAB_AUDIO_PREFLIGHT_SOUND
    global LAB_AUDIO_STREAM_SAMPLE_RATE, LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX
    global LAB_AUDIO_STREAM_PREDICTED_LATENCY_S, LAB_AUDIO_STREAM_STATUS

    LAB_AUDIO_PREFLIGHT_PASSED = False
    LAB_AUDIO_STREAM_SAMPLE_RATE = None
    LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX = None
    LAB_AUDIO_STREAM_PREDICTED_LATENCY_S = None
    LAB_AUDIO_STREAM_STATUS = ''

    if LAB_AUDIO_CONFIG_ERROR:
        raise RuntimeError(LAB_AUDIO_CONFIG_ERROR)
    if not LAB_AUDIO_SELECTED_DEVICE or LAB_AUDIO_SELECTED_DEVICE_INDEX is None:
        LAB_AUDIO_CONFIG_ERROR = 'No verified Focusrite WASAPI output device is available.'
        raise RuntimeError(LAB_AUDIO_CONFIG_ERROR)

    try:
        configured_devices = prefs.hardware.get('audioDevice', [])
    except Exception:
        configured_devices = []
    if isinstance(configured_devices, str):
        configured_devices = [configured_devices]

    if LAB_AUDIO_SELECTED_DEVICE not in [str(value) for value in configured_devices]:
        LAB_AUDIO_CONFIG_ERROR = 'PsychoPy audioDevice preference does not contain the selected Focusrite device.'
        LAB_AUDIO_STREAM_STATUS = LAB_AUDIO_CONFIG_ERROR
        raise RuntimeError(LAB_AUDIO_CONFIG_ERROR)

    try:
        if LAB_AUDIO_SPEAKER is None:
            LAB_AUDIO_SPEAKER = SpeakerDevice(
                name=LAB_AUDIO_SELECTED_DEVICE,
                latencyClass=LAB_AUDIO_LATENCY_MODE,
                resample=True,
            )



        if LAB_AUDIO_PREFLIGHT_SOUND is None:
            LAB_AUDIO_PREFLIGHT_SOUND = sound.Sound(
                'A',
                secs=0.01,
                stereo=True,
                hamming=True,
                name='AudioPreflight',
                autoLog=False,
                speaker=LAB_AUDIO_SPEAKER,
            )
            LAB_AUDIO_PREFLIGHT_SOUND.setVolume(0.0)

        _record_shared_audio_stream_details(LAB_AUDIO_SPEAKER)
        LAB_AUDIO_PREFLIGHT_PASSED = True
        LAB_AUDIO_CONFIG_ERROR = ''
        return True
    except Exception as error:
        LAB_AUDIO_SPEAKER = None
        LAB_AUDIO_PREFLIGHT_SOUND = None
        LAB_AUDIO_CONFIG_ERROR = 'Could not open the Focusrite PTB audio stream: ' + repr(error)
        LAB_AUDIO_STREAM_STATUS = LAB_AUDIO_CONFIG_ERROR
        raise RuntimeError(LAB_AUDIO_CONFIG_ERROR)

configure_ptb_wasapi_audio()

from psychopy import plugins
plugins.activatePlugins()
from psychopy import sound, gui, visual, core, data, event, logging, clock, hardware
from psychopy.hardware import eyetracker as psychopy_eyetracker
from psychopy.hardware.speaker import SpeakerDevice
from psychopy.tools import environmenttools
from psychopy.constants import NOT_STARTED, STARTED, PAUSED, FINISHED, priority
from psychopy.hardware import keyboard
from pyglet.window import key as pyglet_key
from psychopy.iohub import launchHubServer

import numpy as np

sound.Sound.backend = 'ptb'


deviceManager = hardware.DeviceManager()
_thisDir = os.path.dirname(os.path.abspath(__file__))
psychopyVersion = '2026.1.0'
expName = 'labsession1_0'
expVersion = 'labsession1_0'
runAtExit = []
expInfo = {
    'participant': '001',
    'session': '001',
    'date|hid': data.getDateStr(),
    'expName|hid': expName,
    'expVersion|hid': expVersion,
    'psychopyVersion|hid': psychopyVersion,
}


PILOTING = core.setPilotModeFromArgs()
_fullScr = True
_winSize = [1920,1080]
if PILOTING:
    if prefs.piloting['forceWindowed']:
        _fullScr = False
        _winSize = prefs.piloting['forcedWindowSize']
    if prefs.piloting['replaceParticipantID']:
        expInfo['participant'] = 'pilot'







RUN_HAND_SETUP_INSTRUCTION = 1
RUN_CUE_SOUND_PREVIEW = 1
RUN_PRESS_FEEDBACK_PREVIEW = 1
RUN_COIN_SOUND_TEST = 1
RUN_VISUAL_PRACTICE = 1
RUN_EYE_TRACKING_PRACTICE = 1
RUN_MAIN_TASK_SETUP_AND_CALIBRATION = 1
RUN_MAIN_TASK = 1
RUN_SOUND_CHECK = 1






EYETRACKER_BACKEND = 'eyelink'
EYELINK_SAMPLING_RATE = 1000
EYELINK_TRACK_EYES = 'BINOCULAR'
EYETRACKER_SIMULATION_MODE = False


EYELINK_CALIBRATION_LAYOUT = 'NINE_POINTS'
EYELINK_RANDOMISE_CALIBRATION_POSITIONS = True
EYELINK_CALIBRATION_TARGET_DURATION_S = 1.5
EYELINK_CALIBRATION_TARGET_DELAY_S = 1.0
EYELINK_CALIBRATION_AREA_PROPORTION = (0.50, 0.50)
EYELINK_VALIDATION_AREA_PROPORTION = (0.50, 0.50)
EYELINK_CALIBRATION_PACING_INTERVAL_MS = 1000



EYELINK_PUPIL_SIZE_OUTPUT = 'DIAMETER'
EYELINK_FILE_EVENT_DATA_FIELDS = 'GAZE,HREF,AREA,STATUS'
EYELINK_FILE_SAMPLE_DATA_FIELDS = 'LEFT,RIGHT,GAZE,HREF,PUPIL,AREA,STATUS'
EYELINK_LINK_EVENT_DATA_FIELDS = 'GAZE,HREF,AREA,STATUS'
EYELINK_LINK_SAMPLE_DATA_FIELDS = 'LEFT,RIGHT,GAZE,HREF,PUPIL,AREA,STATUS'
EYELINK_EVENT_FILTER_FIELDS = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON'

def _eyelink_pair_value(value):
    return f'{float(value[0]):.2f} {float(value[1]):.2f}'


EYELINK_HOST_COMMANDS = [
    ('calibration_area_proportion', _eyelink_pair_value(EYELINK_CALIBRATION_AREA_PROPORTION)),
    ('validation_area_proportion', _eyelink_pair_value(EYELINK_VALIDATION_AREA_PROPORTION)),
    ('automatic_calibration_pacing', str(int(EYELINK_CALIBRATION_PACING_INTERVAL_MS))),
    ('pupil_size_diameter', 'YES'),
    ('file_event_filter', EYELINK_EVENT_FILTER_FIELDS),
    ('file_event_data', EYELINK_FILE_EVENT_DATA_FIELDS),
    ('file_sample_data', EYELINK_FILE_SAMPLE_DATA_FIELDS),
    ('link_event_filter', EYELINK_EVENT_FILTER_FIELDS),
    ('link_event_data', EYELINK_LINK_EVENT_DATA_FIELDS),
    ('link_sample_data', EYELINK_LINK_SAMPLE_DATA_FIELDS),
]

def send_eyelink_host_command(tracker, command_name, command_value):

    try:
        return tracker.sendCommand(command_name, command_value)
    except TypeError:
        return tracker.sendCommand(f'{command_name} = {command_value}')



GAZE_BOUNDARY_RADIUS = 0.08


GAZE_BREAK_MIN_DURATION = 0.300


IOHUB_GAZE_UNKNOWN_UNIT_FALLBACK = 'pix'


SHOW_MOUSE_CURSOR_DURING_EYETRACKING = False



def showExpInfoDlg(expInfo):
    dlg = gui.DlgFromDict(
        dictionary=expInfo, sortKeys=False, title=expName
    )
    if dlg.OK == False:
        core.quit()

    participant_id_text = str(expInfo.get('participant', '')).strip()
    if not participant_id_text.isdigit() or int(participant_id_text) < 1:
        errorDlg = gui.Dlg(title='Participant ID error')
        errorDlg.addText(
            'Participant ID must be a positive number, for example 001, 002, 003.\n\n'
            'This is needed for balanced cue assignment.'
        )
        errorDlg.show()
        core.quit()
    return expInfo


def setupData(expInfo, dataDir=None):

    for key, val in expInfo.copy().items():
        newKey, _ = data.utils.parsePipeSyntax(key)
        expInfo[newKey] = expInfo.pop(key)

    if dataDir is None:
        dataDir = _thisDir
    data_folder = os.path.join(dataDir, 'data')
    os.makedirs(data_folder, exist_ok=True)

    participant = re.sub(r'[^A-Za-z0-9_-]', '', str(expInfo.get('participant', '001'))) or '001'
    session = re.sub(r'[^A-Za-z0-9_-]', '', str(expInfo.get('session', '001'))) or '001'
    file_stem = f'participant-{participant}_session-{session}_{expName}_{expInfo["date"]}'
    filename = os.path.join('data', file_stem)

    thisExp = data.ExperimentHandler(
        name=expName,
        version=expVersion,
        extraInfo=expInfo,
        runtimeInfo=None,
        originPath=__file__,
        savePickle=False,
        saveWideText=True,
        dataFileName=os.path.join(dataDir, filename)
    )
    if not hasattr(thisExp, 'dataFileName') or thisExp.dataFileName in [None, '']:
        thisExp.dataFileName = os.path.join(dataDir, filename)

    thisExp.addData('participant_id', participant, priority=priority.LOW)
    thisExp.addData('session_id', session, priority=priority.LOW)
    thisExp.addData('behavioural_data_stem', thisExp.dataFileName, priority=priority.LOW)
    thisExp.addData('piloting', PILOTING, priority=priority.LOW)
    if hasattr(thisExp, 'setPriority'):
        thisExp.setPriority('thisRow.t', priority.CRITICAL)
        thisExp.setPriority('expName', priority.LOW)
    return thisExp


def logging_level(level, default=None):

    if default is None:
        default = logging.WARNING
    if isinstance(level, int):
        return level
    try:
        if isinstance(level, str):
            return getattr(logging, level.upper())
    except Exception:
        pass
    try:
        converted = logging.getLevel(level)
        if isinstance(converted, int):
            return converted
    except Exception:
        pass
    return default

def setupLogging(filename):
    if PILOTING:
        logging.console.setLevel(logging_level(prefs.piloting.get('pilotConsoleLoggingLevel', logging.WARNING)))
    else:
        logging.console.setLevel(logging.WARNING)
    logFile = logging.LogFile(filename+'.log')
    if PILOTING:
        logFile.setLevel(logging_level(prefs.piloting.get('pilotLoggingLevel', logging.INFO), logging.INFO))
    else:
        logFile.setLevel(logging.INFO)

    return logFile


def setupWindow(expInfo=None, win=None):

    monitor_profile = 'default'
    if win is None:
        win = visual.Window(
            size=_winSize, fullscr=_fullScr, screen=0,
            winType='pyglet', allowGUI=False, allowStencil=False,
            color=[0, 0, 0], colorSpace='rgb',
            blendMode='avg', useFBO=True,
            units='height'
        )
    else:
        win.color = [0, 0, 0]
        win.colorSpace = 'rgb'
        win.units = 'height'

    measured_frame_rate = None
    try:
        measured_frame_rate = win.getActualFrameRate(
            nIdentical=20, nMaxFrames=240, nWarmUpFrames=60, threshold=1
        )
    except Exception as e:
        logging.warning('Could not measure display frame rate: ' + repr(e))
    if measured_frame_rate is None:
        try:
            measured_frame_rate = 1.0 / float(win.monitorFramePeriod)
        except Exception:
            measured_frame_rate = None

    if expInfo is not None:
        expInfo['monitor_profile'] = monitor_profile
        expInfo['frameRate_measuredHz'] = measured_frame_rate
        expInfo['frameRate'] = measured_frame_rate


    win.recordFrameIntervals = True
    win.hideMessage()
    win.mouseVisible = True
    if PILOTING:
        if prefs.piloting['showPilotingIndicator'] and hasattr(win, 'showPilotingIndicator'):
            win.showPilotingIndicator()
        if prefs.piloting['forceMouseVisible']:
            win.mouseVisible = True
    return win


def make_safe_code(value, fallback='X', max_len=None):

    value = re.sub(r'[^A-Za-z0-9]', '', str(value)).upper()
    if not value:
        value = fallback
    if max_len is not None:
        value = value[:max_len]
    return value


def make_eyelink_edf_basename(expInfo):





    participant = make_safe_code(expInfo.get('participant', '001'), fallback='001')
    session = make_safe_code(expInfo.get('session', '001'), fallback='001')
    return ('P' + participant + 'S' + session)[:8]


def make_iohub_session_code(expInfo):

    participant = make_safe_code(expInfo.get('participant', '001'), fallback='001')
    session = make_safe_code(expInfo.get('session', '001'), fallback='001')
    return (participant + '_' + session)[:24]


def make_eye_data_stem(expInfo):
    participant = re.sub(r'[^A-Za-z0-9_-]', '', str(expInfo.get('participant', '001'))) or '001'
    session = re.sub(r'[^A-Za-z0-9_-]', '', str(expInfo.get('session', '001'))) or '001'
    date_code = re.sub(r'[^A-Za-z0-9_-]', '', str(expInfo.get('date', data.getDateStr()))) or data.getDateStr()
    return f'participant-{participant}_session-{session}_{expName}_{date_code}'


def eye_data_output_dirs(thisExp):
    data_stem = getattr(thisExp, 'dataFileName', os.path.join(_thisDir, 'data', 'last_run'))
    data_dir = os.path.dirname(os.path.abspath(data_stem))
    edf_dir = os.path.join(data_dir, 'EDF')
    hdf5_dir = os.path.join(data_dir, 'iohub_hdf5')
    os.makedirs(edf_dir, exist_ok=True)
    os.makedirs(hdf5_dir, exist_ok=True)
    return data_dir, edf_dir, hdf5_dir


def eye_data_candidate_paths(search_dirs):
    candidates = []
    seen = set()
    for directory in search_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        try:
            for entry in os.scandir(directory):
                if not entry.is_file():
                    continue
                name = entry.name.lower()
                if name.endswith(('.edf', '.hdf5', '.h5')) or name in ('et_data', 'et_data.edf', 'et_data.hdf5'):
                    path = os.path.abspath(entry.path)
                    if path not in seen:
                        candidates.append(path)
                        seen.add(path)
        except OSError:
            pass
    return candidates


def snapshot_eye_data_candidates(search_dirs):
    snapshot = {}
    for path in eye_data_candidate_paths(search_dirs):
        try:
            stat = os.stat(path)
            snapshot[path] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            pass
    return snapshot


def changed_eye_data_candidates(search_dirs, before_snapshot, started_at_epoch):
    changed = []
    for path in eye_data_candidate_paths(search_dirs):
        try:
            stat = os.stat(path)
        except OSError:
            continue
        previous = before_snapshot.get(path)
        changed_since_start = stat.st_mtime >= (started_at_epoch - 1.0)
        if previous is None or previous != (stat.st_size, stat.st_mtime_ns) or changed_since_start:
            changed.append(path)
    return changed


def move_eye_data_file(source_path, destination_dir, output_stem, extension):
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir, output_stem + extension)
    suffix = 1
    while os.path.exists(destination):
        destination = os.path.join(destination_dir, f'{output_stem}_{suffix:02d}{extension}')
        suffix += 1
    shutil.move(source_path, destination)
    return os.path.abspath(destination)

def setupDevices(expInfo, thisExp, win):

    global EYETRACKER_BACKEND

    participant = str(expInfo.get('participant', '001'))
    session = str(expInfo.get('session', '001'))
    requested_edf_basename = make_eyelink_edf_basename(expInfo)
    iohub_session_code = make_iohub_session_code(expInfo)
    iohub_datastore_name = make_eye_data_stem(expInfo)
    data_dir, edf_dir, hdf5_dir = eye_data_output_dirs(thisExp)
    scan_dirs = [_thisDir, data_dir]
    initial_eye_data_snapshot = snapshot_eye_data_candidates(scan_dirs)
    iohub_launch_started_at = time.time()

    expInfo['eyelink_requested_edf_basename'] = requested_edf_basename
    expInfo['iohub_participant'] = participant
    expInfo['iohub_session'] = session
    expInfo['iohub_session_code'] = iohub_session_code
    expInfo['iohub_datastore_name'] = iohub_datastore_name
    expInfo['eyelink_output_directory'] = edf_dir
    expInfo['iohub_hdf5_output_directory'] = hdf5_dir
    try:
        thisExp.extraInfo['eyelink_requested_edf_basename'] = requested_edf_basename
        thisExp.extraInfo['iohub_participant'] = participant
        thisExp.extraInfo['iohub_session'] = session
        thisExp.extraInfo['iohub_session_code'] = iohub_session_code
        thisExp.extraInfo['iohub_datastore_name'] = iohub_datastore_name
        thisExp.extraInfo['eyelink_output_directory'] = edf_dir
        thisExp.extraInfo['iohub_hdf5_output_directory'] = hdf5_dir
    except Exception:
        pass
    thisExp._eye_data_scan_dirs = scan_dirs
    thisExp._eye_data_initial_snapshot = initial_eye_data_snapshot
    thisExp._iohub_launch_started_at = iohub_launch_started_at
    thisExp.addData('eyelink_requested_edf_basename', requested_edf_basename)
    thisExp.addData('iohub_participant', participant)
    thisExp.addData('iohub_session', session)
    thisExp.addData('iohub_session_code', iohub_session_code)
    thisExp.addData('iohub_datastore_name', iohub_datastore_name)
    thisExp.addData('eyelink_output_directory', edf_dir)
    thisExp.addData('iohub_hdf5_output_directory', hdf5_dir)
    thisExp.nextEntry()

    if EYETRACKER_BACKEND.lower() == 'mousegaze':
        iohub_config = {
            'eyetracker.hw.mouse.EyeTracker': {
                'name': 'tracker'
            }
        }
    elif EYETRACKER_BACKEND.lower() == 'eyelink':
        eyelink_settings = {
            'name': 'tracker',
            'simulation_mode': EYETRACKER_SIMULATION_MODE,
        }

        runtime_settings = {}
        if isinstance(EYELINK_SAMPLING_RATE, int):
            runtime_settings['sampling_rate'] = EYELINK_SAMPLING_RATE
        if isinstance(EYELINK_TRACK_EYES, str) and EYELINK_TRACK_EYES.lower() not in ['auto', 'default', '']:
            runtime_settings['track_eyes'] = EYELINK_TRACK_EYES
        if runtime_settings:
            eyelink_settings['runtime_settings'] = runtime_settings

        iohub_config = {
            'eyetracker.hw.sr_research.eyelink.EyeTracker': eyelink_settings
        }
    else:
        raise RuntimeError("Unsupported EYETRACKER_BACKEND. Use 'eyelink' or 'mousegaze'.")

    iohub_launch_kwargs = {
        'window': win,
        'experiment_code': expName,
        'session_code': iohub_session_code,
        'datastore_name': iohub_datastore_name,
        'experiment_info': {
            'code': expName,
            'title': expName,
            'version': expVersion,
        },
        'session_info': {
            'code': iohub_session_code,
            'name': iohub_datastore_name,
            'user_variables': {
                'participant': participant,
                'session': session,
            },
        },
    }
    try:
        ioServer = launchHubServer(**iohub_launch_kwargs, **iohub_config)
    except Exception as e:
        raise

    deviceManager.ioServer = ioServer

    try:
        tracker_setup = ioServer.devices.tracker
    except Exception as e:
        tracker_setup = None

    try:
        if tracker_setup is not None and hasattr(tracker_setup, 'sendCommand'):
            command_errors = []
            for cmd_name, cmd_value in EYELINK_HOST_COMMANDS:
                try:
                    send_eyelink_host_command(tracker_setup, cmd_name, cmd_value)
                    thisExp.addData(f'eyelink_command_{cmd_name}_value', cmd_value)
                    thisExp.addData(f'eyelink_command_{cmd_name}_sent', True)
                except Exception as cmd_error:
                    command_errors.append(f'{cmd_name}: {repr(cmd_error)}')
                    thisExp.addData(f'eyelink_command_{cmd_name}_value', cmd_value)
                    thisExp.addData(f'eyelink_command_{cmd_name}_sent', False)
                    thisExp.addData(f'eyelink_command_{cmd_name}_error', repr(cmd_error))
            thisExp.addData('eyelink_host_command_error_count', len(command_errors))
            if command_errors:
                thisExp.addData('eyelink_host_command_errors', ' | '.join(command_errors))
            thisExp.nextEntry()
    except Exception as e:
        thisExp.addData('eyelink_setup_command_error', repr(e))
        thisExp.nextEntry()

    if deviceManager.getDevice('defaultKeyboard') is None:
        try:
            kb = keyboard.Keyboard()
            if hasattr(deviceManager, '_devices'):
                deviceManager._devices['defaultKeyboard'] = kb
        except Exception:
            pass

    return True


def pauseExperiment(thisExp, win=None, timers=[], currentRoutine=None):
    if thisExp.status != PAUSED:
        return

    pauseTimer = core.Clock()
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.pause()
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        defaultKeyboard = keyboard.Keyboard()
        if hasattr(deviceManager, '_devices'):
            deviceManager._devices['defaultKeyboard'] = defaultKeyboard
    while thisExp.status == PAUSED:
        if defaultKeyboard.getKeys(keyList=['escape']):
            endExperiment(thisExp, win=win)
        if currentRoutine is not None:
            for comp in currentRoutine.getDispatchComponents():
                comp.device.dispatchMessages()
        clock.time.sleep(0.001)
    if thisExp.status == FINISHED:
        endExperiment(thisExp, win=win)
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.play()
    for timer in timers:
        timer.addTime(-pauseTimer.getTime())


def run(expInfo, thisExp, win, globalClock=None, thisSession=None):
    thisExp.status = STARTED
    expInfo['date'] = data.getDateStr()
    expInfo['expName'] = expName
    expInfo['expVersion'] = expVersion
    expInfo['psychopyVersion'] = psychopyVersion
    try:
        win.winHandle.activate()
    except Exception:
        pass
    exec = environmenttools.setExecEnvironment(globals())
    ioServer = deviceManager.ioServer
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        defaultKeyboard = keyboard.Keyboard()
        if hasattr(deviceManager, '_devices'):
            deviceManager._devices['defaultKeyboard'] = defaultKeyboard
    eyetracker = None

    try:
        verify_ptb_wasapi_audio_configuration()
    except Exception as audio_error:
        error_text = str(audio_error)
        thisExp.addData('audio_preflight_passed', False)
        thisExp.addData('audio_stream_sample_rate_hz', LAB_AUDIO_STREAM_SAMPLE_RATE)
        thisExp.addData('audio_stream_output_device_index', LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX)
        thisExp.addData('audio_stream_predicted_latency_s', LAB_AUDIO_STREAM_PREDICTED_LATENCY_S)
        thisExp.addData('audio_stream_status', LAB_AUDIO_STREAM_STATUS or error_text)
        thisExp.addData('audio_config_error', error_text)
        thisExp.nextEntry()
        try:
            audio_error_dialog = gui.Dlg(title='Audio setup issue')
            audio_error_dialog.addText(
                'The task could not start because of an audio setup issue.\n\n'
                'Please contact the researcher.'
            )
            audio_error_dialog.show()
        except Exception:
            pass
        thisExp.status = FINISHED
        return

    def get_eyetracker():

        io = deviceManager.ioServer
        if io is None:
            return None

        try:
            tracker = io.devices.tracker
            if tracker is not None:
                return tracker
        except Exception:
            pass

        for devName in ['tracker', 'eyetracker']:
            try:
                tracker = io.getDevice(devName)
                if tracker is not None:
                    return tracker
            except Exception:
                pass

        return None


    eyetracker = get_eyetracker()


    def run_eye_calibration(label):






        tracker = get_eyetracker()

        try:
            thisExp.addData(f'eyetracker_calibration_{label}_started', globalClock.getTime(format='float'))
        except Exception:
            thisExp.addData(f'eyetracker_calibration_{label}_started', core.getTime())
        thisExp.addData(f'eyetracker_calibration_{label}_method', 'psychopy_iohub_calibration')
        thisExp.nextEntry()

        def _show_calibration_problem(message):
            try:
                thisExp.addData(f'eyetracker_calibration_{label}_error', str(message))
                thisExp.nextEntry()
            except Exception:
                pass

            txt = (
                'Eye-tracker setup did not finish correctly.\n\n'
                'Press R to try again.\n'
                'Press ESC to quit.'
            )
            errStim = visual.TextStim(
                win=win, name='calibrationErrorText', text=txt,
                font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
            )
            rWasDown = vk_down(0x52)
            escWasDown = vk_down(0x1B)
            while True:
                errStim.draw()
                rDown = vk_down(0x52)
                escDown = vk_down(0x1B)
                if rDown and not rWasDown:
                    routineTimer.reset()
                    return 'retry'
                if escDown and not escWasDown:
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return 'quit'
                rWasDown = rDown
                escWasDown = escDown
                win.flip()

        def _clear_keyboard_events():
            try:
                defaultKeyboard.clearEvents()
            except Exception:
                try:
                    event.clearEvents(eventType='keyboard')
                except Exception:
                    pass

        def _make_calibration_target(name):

            return visual.TargetStim(
                win,
                name=name,
                radius=0.0175,
                fillColor=None,
                borderColor='white',
                lineWidth=2.0,
                innerRadius=0.00875,
                innerFillColor='white',
                innerBorderColor='white',
                innerLineWidth=2.0,
                colorSpace='rgb',
                units=None
            )

        def _run_calibration_setup_once():
            tracker_now = get_eyetracker()
            if tracker_now is None and EYETRACKER_BACKEND.lower() != 'mousegaze':
                raise RuntimeError('ioHub eye tracker object is missing.')
            try:
                if tracker_now is not None:
                    tracker_now.setRecordingState(False)
            except Exception:
                pass

            if tracker_now is not None and hasattr(tracker_now, 'sendCommand'):
                command_errors = []
                for cmd_name, cmd_value in EYELINK_HOST_COMMANDS:
                    try:
                        send_eyelink_host_command(tracker_now, cmd_name, cmd_value)
                    except Exception as cmd_error:
                        command_errors.append(f'{cmd_name}: {repr(cmd_error)}')
                if command_errors:
                    raise RuntimeError(
                        'EyeLink Host command error(s): ' + ' | '.join(command_errors)
                    )

            old_color = getattr(win, 'color', [0, 0, 0])
            old_mouse_visible = getattr(win, 'mouseVisible', False)
            try:
                win.color = [0, 0, 0]
                win.mouseVisible = False
                win.flip()

                calibrationTarget = _make_calibration_target('calibrationTarget')
                calibrationClass = None
                if psychopy_eyetracker is not None and hasattr(psychopy_eyetracker, 'EyetrackerCalibration'):
                    calibrationClass = psychopy_eyetracker.EyetrackerCalibration
                elif hasattr(hardware, 'eyetracker') and hasattr(hardware.eyetracker, 'EyetrackerCalibration'):
                    calibrationClass = hardware.eyetracker.EyetrackerCalibration

                if calibrationClass is not None:
                    calibration = calibrationClass(
                        win,
                        tracker_now,
                        calibrationTarget,
                        units=None,
                        colorSpace='rgb',
                        progressMode='time',
                        targetDur=EYELINK_CALIBRATION_TARGET_DURATION_S,
                        expandScale=0.24,
                        targetLayout=EYELINK_CALIBRATION_LAYOUT,
                        randomisePos=EYELINK_RANDOMISE_CALIBRATION_POSITIONS,
                        textColor='white',
                        movementAnimation=True,
                        targetDelay=EYELINK_CALIBRATION_TARGET_DELAY_S
                    )
                    calResult = calibration.run()
                elif tracker_now is not None and hasattr(tracker_now, 'runSetupProcedure'):
                    calResult = tracker_now.runSetupProcedure()
                else:
                    raise RuntimeError('No supported PsychoPy/ioHub eye-tracker calibration method was found.')

                _clear_keyboard_events()
                return calResult
            finally:
                try:
                    win.color = old_color
                except Exception:
                    pass
                try:
                    win.mouseVisible = old_mouse_visible
                except Exception:
                    pass
                try:
                    win.flip()
                except Exception:
                    pass

        while True:
            try:
                calResult = _run_calibration_setup_once()
                try:
                    completed_time = globalClock.getTime(format='float')
                except Exception:
                    completed_time = core.getTime()

                thisExp.addData(f'eyetracker_calibration_{label}_completed', completed_time)
                thisExp.addData(f'eyetracker_calibration_{label}_result', str(calResult))
                thisExp.addData(f'eyetracker_calibration_{label}_host_procedure_returned', True)
                thisExp.addData(f'eyetracker_calibration_{label}_validation_handled_by', 'eyelink_host')
                thisExp.nextEntry()

                routineTimer.reset()
                return True
            except Exception as e:
                choice = _show_calibration_problem(repr(e))
                if choice == 'retry':
                    continue
                return False


    def start_eye_recording(label):




        tracker = get_eyetracker()

        if tracker is None:
            thisExp.addData(f'eyetracker_recording_{label}_error', 'eyetracker_missing')
            thisExp.nextEntry()
            return False

        try:
            tracker.setRecordingState(True)
            thisExp.addData(f'eyetracker_recording_{label}_started', globalClock.getTime(format='float'))
            thisExp.nextEntry()
            return True
        except Exception as e:
            thisExp.addData(f'eyetracker_recording_{label}_error', str(e))
            thisExp.nextEntry()
            return False


    def stop_eye_recording(label):



        tracker = get_eyetracker()

        if tracker is None:
            return

        try:
            tracker.setRecordingState(False)
            thisExp.addData(f'eyetracker_recording_{label}_stopped', globalClock.getTime(format='float'))
            thisExp.nextEntry()
        except Exception as e:
            thisExp.addData(f'eyetracker_recording_{label}_stop_error', str(e))
            thisExp.nextEntry()

    os.chdir(_thisDir)
    filename = getattr(thisExp, 'dataFileName', os.path.join(_thisDir, 'data', 'last_run'))


    main_trial_csv_path = filename + '_main_trials.csv'
    main_trial_csv_fields = [
        'participant_id', 'session_id', 'task_date',
        'block', 'trial', 'completed_attempt', 'condition_index', 'cue_identity',
        'cue_version', 'cue_file', 'FR', 'magnitude_pence', 'feedback_file',
        'baseline_start_global', 'cue_visual_onset_global', 'cue_audio_planned_onset_global',
        'cue_audio_planned_onset_ptb', 'cue_audio_scheduled_with_ptb',
        'plus_visual_onset_global', 'iti_start_global', 'click_duration_s',
        'early_press_count', 'early_press_rts_s', 'early_press_global_times_s',
        'valid_press_count', 'valid_press_rts_s', 'valid_press_global_times_s',
        'invalid_press_count', 'invalid_press_rts_s', 'invalid_press_global_times_s',
        'reward_count', 'reward_trigger_press_rts_s', 'reward_trigger_press_global_times_s',
        'reward_audio_planned_onsets_global_s', 'reward_audio_planned_onsets_ptb_s',
        'earned_pence',
        'minimum_possible_earnings_pence', 'maximum_possible_earnings_pence'
    ]
    main_trial_csv_file = open(main_trial_csv_path, 'w', newline='', encoding='utf-8')
    main_trial_csv_writer = csv.DictWriter(main_trial_csv_file, fieldnames=main_trial_csv_fields)
    main_trial_csv_writer.writeheader()
    main_trial_csv_file.flush()
    thisExp.addData('main_trial_csv_path', main_trial_csv_path)


    final_sound_check_bonus_csv_path = filename + '_final_sound_check_bonus.csv'
    final_sound_check_bonus_csv_fields = [
        'record_type', 'participant_id', 'session_id', 'task_date',
        'sound_check_enabled', 'sound_check_block', 'sound_check_trial',
        'sound_check_sequence_trial', 'sound_check_question', 'sound_check_display_format',
        'option1_key', 'option2_key',
        'option1_condition_index', 'option2_condition_index',
        'option1_cue_identity', 'option2_cue_identity',
        'option1_cue_file', 'option2_cue_file',
        'option1_cue_image', 'option2_cue_image',
        'option1_label', 'option2_label',
        'option1_FR', 'option2_FR',
        'option1_magnitude_pence', 'option2_magnitude_pence',
        'option1_metric', 'option2_metric',
        'correct_position', 'choice_position', 'choice_key', 'confirmation_key',
        'first_selection_key', 'first_selection_rt_s', 'sound_play_count',
        'response_rt_s', 'score',
        'sound_check_total_trials', 'sound_check_total_correct',
        'sound_check_total_incorrect', 'sound_check_accuracy',
        'main_actual_earnings_pence', 'main_minimum_possible_earnings_pence',
        'main_maximum_possible_earnings_pence', 'main_earning_ratio_raw',
        'main_earning_ratio', 'main_bonus_GBP', 'main_bonus_GBP_rounded_to_pence'
    ]
    final_sound_check_bonus_csv_file = open(
        final_sound_check_bonus_csv_path, 'w', newline='', encoding='utf-8'
    )
    final_sound_check_bonus_csv_writer = csv.DictWriter(
        final_sound_check_bonus_csv_file,
        fieldnames=final_sound_check_bonus_csv_fields
    )
    final_sound_check_bonus_csv_writer.writeheader()
    final_sound_check_bonus_csv_file.flush()
    thisExp.addData('final_sound_check_bonus_csv_path', final_sound_check_bonus_csv_path)


    task_event_csv_path = filename + '_events.csv'
    task_event_csv_file = open(task_event_csv_path, 'w', newline='', encoding='utf-8')
    task_event_csv_writer = csv.DictWriter(
        task_event_csv_file,
        fieldnames=['event_name', 'event_time_global', 'fields_json']
    )
    task_event_csv_writer.writeheader()
    task_event_csv_file.flush()
    thisExp.addData('task_event_csv_path', task_event_csv_path)

    def _csv_cell(value):
        if isinstance(value, (list, tuple, dict)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def write_main_trial_record(record):
        row = {field: _csv_cell(record.get(field, '')) for field in main_trial_csv_fields}
        main_trial_csv_writer.writerow(row)
        main_trial_csv_file.flush()

    def write_task_event_record(event_name, event_time, fields):
        task_event_csv_writer.writerow({
            'event_name': str(event_name),
            'event_time_global': float(event_time),
            'fields_json': json.dumps(fields, ensure_ascii=False, default=str),
        })
        task_event_csv_file.flush()

    def write_final_sound_check_bonus_record(record):
        row = {
            field: _csv_cell(record.get(field, ''))
            for field in final_sound_check_bonus_csv_fields
        }
        final_sound_check_bonus_csv_writer.writerow(row)
        final_sound_check_bonus_csv_file.flush()

    frameTolerance = 0.001
    endExpNow = False

    if 'frameRate' in expInfo and expInfo['frameRate']:
        frameDur = 1.0 / float(expInfo['frameRate'])
    else:
        frameDur = float(getattr(win, 'monitorFramePeriod', 1.0 / 60.0))


    CONTENT_X_LIMIT = 0.52
    CONTENT_Y_LIMIT = 0.30
    CENTRAL_TEXT_WRAP = 0.92
    CENTRAL_TEXT_TOP_Y = 0.185
    CENTRAL_TEXT_MID_Y = 0.025
    CENTRAL_TEXT_LOW_Y = -0.090


    TASK_TEXT_HEIGHT = 0.032
    TASK_TEXT_MIN_HEIGHT = 0.028


    BOTTOM_PROMPT_Y = -0.300
    BOTTOM_PROMPT_WRAP = 0.92

    def fitted_text_height(text, preferred=TASK_TEXT_HEIGHT, minimum=TASK_TEXT_MIN_HEIGHT, available_height=0.42):

        n_lines = max(1, len(str(text).split('\n')))
        max_height = available_height / (n_lines * 1.20)
        return max(minimum, min(float(preferred), max_height))
    instr = visual.TextStim(win=win, name='instr',
    text="Before we start, which hand do you write with?\n\nPress X for left hand.\nPress M for right hand.",
        font='Arial',
        pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT, wrapWidth=CENTRAL_TEXT_WRAP, ori=0.0,
        color='white', colorSpace='rgb', opacity=None,
        depth=0.0);
    startspace = keyboard.Keyboard()
    baseDir = _thisDir

    pilotSectionFlags = {
        'RUN_HAND_SETUP_INSTRUCTION': RUN_HAND_SETUP_INSTRUCTION,
        'RUN_CUE_SOUND_PREVIEW': RUN_CUE_SOUND_PREVIEW,
        'RUN_PRESS_FEEDBACK_PREVIEW': RUN_PRESS_FEEDBACK_PREVIEW,
        'RUN_COIN_SOUND_TEST': RUN_COIN_SOUND_TEST,
        'RUN_VISUAL_PRACTICE': RUN_VISUAL_PRACTICE,
        'RUN_EYE_TRACKING_PRACTICE': RUN_EYE_TRACKING_PRACTICE,
        'RUN_MAIN_TASK_SETUP_AND_CALIBRATION': RUN_MAIN_TASK_SETUP_AND_CALIBRATION,
        'RUN_MAIN_TASK': RUN_MAIN_TASK,
        'RUN_SOUND_CHECK': RUN_SOUND_CHECK,
    }
    for flagName, flagValue in pilotSectionFlags.items():
        thisExp.addData(flagName, flagValue)
    thisExp.addData('softwareHoldKeyDetectionEnforcedAtResponse', True)
    thisExp.addData('labKeyMapping_left_hold', 'F,T,H')
    thisExp.addData('labKeyMapping_left_response', 'X')
    thisExp.addData('labKeyMapping_right_hold', 'F,T,H')
    thisExp.addData('labKeyMapping_right_response', 'M')
    thisExp.addData('task_code_version', 'labsession1_0')
    thisExp.addData('audio_stream_strategy', 'single_shared_focusrite_stream_preopened_before_task')
    thisExp.addData('audio_backend_requested', 'PTB')
    thisExp.addData('audio_driver_requested', 'PTB_Focusrite_WASAPI_shared_stream')
    thisExp.addData('audio_latency_mode_requested', LAB_AUDIO_LATENCY_MODE)
    thisExp.addData('audio_sample_rate_target', LAB_AUDIO_SAMPLE_RATE_TARGET)
    thisExp.addData('audio_selected_device', LAB_AUDIO_SELECTED_DEVICE)
    thisExp.addData('audio_selected_device_index', LAB_AUDIO_SELECTED_DEVICE_INDEX)
    thisExp.addData('audio_selected_device_host_api', LAB_AUDIO_SELECTED_HOST_API)
    thisExp.addData('audio_selected_device_output_channels', LAB_AUDIO_SELECTED_OUTPUT_CHANNELS)
    thisExp.addData('audio_selected_device_info', LAB_AUDIO_SELECTED_DEVICE_INFO)
    thisExp.addData('audio_selected_device_default_sample_rate', LAB_AUDIO_SELECTED_DEVICE_DEFAULT_SAMPLE_RATE)
    thisExp.addData('audio_stream_sample_rate_hz', LAB_AUDIO_STREAM_SAMPLE_RATE)
    thisExp.addData('audio_stream_output_device_index', LAB_AUDIO_STREAM_OUTPUT_DEVICE_INDEX)
    thisExp.addData('audio_stream_predicted_latency_s', LAB_AUDIO_STREAM_PREDICTED_LATENCY_S)
    thisExp.addData('audio_stream_status', LAB_AUDIO_STREAM_STATUS)
    thisExp.addData('audio_preflight_passed', LAB_AUDIO_PREFLIGHT_PASSED)
    thisExp.addData('audio_actual_acoustic_latency_verified', False)
    thisExp.addData('audio_timing_reference', 'ptb_planned_onset')
    thisExp.addData('audio_config_error', LAB_AUDIO_CONFIG_ERROR)
    thisExp.addData('eyelink_sampling_rate_requested_hz', EYELINK_SAMPLING_RATE)
    thisExp.addData('eyelink_track_eyes_requested', EYELINK_TRACK_EYES)
    thisExp.addData('eyelink_pupil_size_output_requested', EYELINK_PUPIL_SIZE_OUTPUT)
    thisExp.addData('eyelink_file_event_data_fields_requested', EYELINK_FILE_EVENT_DATA_FIELDS)
    thisExp.addData('eyelink_file_sample_data_fields_requested', EYELINK_FILE_SAMPLE_DATA_FIELDS)
    thisExp.addData('eyelink_link_event_data_fields_requested', EYELINK_LINK_EVENT_DATA_FIELDS)
    thisExp.addData('eyelink_link_sample_data_fields_requested', EYELINK_LINK_SAMPLE_DATA_FIELDS)
    thisExp.addData('eyelink_calibration_layout_requested', EYELINK_CALIBRATION_LAYOUT)
    thisExp.addData('eyelink_calibration_randomised_requested', EYELINK_RANDOMISE_CALIBRATION_POSITIONS)
    thisExp.addData('eyelink_calibration_area_proportion_requested', _eyelink_pair_value(EYELINK_CALIBRATION_AREA_PROPORTION))
    thisExp.addData('eyelink_validation_area_proportion_requested', _eyelink_pair_value(EYELINK_VALIDATION_AREA_PROPORTION))
    thisExp.addData('eyelink_calibration_pacing_interval_ms_requested', EYELINK_CALIBRATION_PACING_INTERVAL_MS)
    thisExp.nextEntry()

    keyState = pyglet_key.KeyStateHandler()
    win.winHandle.push_handlers(keyState)


    def vk_down(vk_code):
        try:
            if (ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000) != 0:
                return True
        except Exception:
            pass

        vk_to_pyglet = {
            0x46: pyglet_key.F,
            0x54: pyglet_key.T,
            0x48: pyglet_key.H,
            0x58: pyglet_key.X,
            0x4D: pyglet_key.M,
            0x20: pyglet_key.SPACE,
            0x1B: pyglet_key.ESCAPE,
        }
        symbol = vk_to_pyglet.get(vk_code)
        if symbol is None:
            return False

        try:
            return bool(keyState[symbol])
        except Exception:
            return False

    def hold_keys_ok(key_codes):
        return all(vk_down(k) for k in key_codes)

    VK_F = 0x46
    VK_T = 0x54
    VK_H = 0x48
    VK_X = 0x58
    VK_M = 0x4D
    circle_fix1 = visual.ShapeStim(
        win=win, name='circle_fix1',
        size=[0.035,0.035], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=0.0, interpolate=True)
    fix_ = visual.TextStim(win=win, name='fix_',
        text='×',
        font='Arial Bold',
        pos=[0,0], height=0.035, wrapWidth=None, ori=0.0,
        color='white', colorSpace='rgb', opacity=None,
        depth=-1.0);
    circle_fix2 = visual.ShapeStim(
        win=win, name='circle_fix2',
        size=[0.0175,0.0175], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=-2.0, interpolate=True)
    circle_cue1 = visual.ShapeStim(
        win=win, name='circle_cue1',
        size=[0.035,0.035], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=0.0, interpolate=True)
    circle_cue2 = visual.ShapeStim(
        win=win, name='circle_cue2',
        size=[0.0175,0.0175], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=-1.0, interpolate=True)
    cue_ = visual.TextStim(win=win, name='cue_',
        text='×',
        font='Arial Bold',
        pos=[0,0], height=0.035, wrapWidth=None, ori=0.0,
        color='white', colorSpace='rgb', opacity=None,
        depth=-2.0);
    try:
        sound.Sound.backend = 'ptb'
    except Exception:
        pass

    def make_lab_sound(*args, **kwargs):

        if LAB_AUDIO_SPEAKER is None:
            raise RuntimeError('The shared task audio stream is not available.')
        kwargs.setdefault('speaker', LAB_AUDIO_SPEAKER)
        return sound.Sound(*args, **kwargs)

    REWARD_SOUND_OVERLAP_ENABLED = True
    REWARD_SOUND_VOLUME = 0.70

    CueSound = make_lab_sound(
        'A',
        secs=1.4,
        stereo=True,
        hamming=True,
        name='CueSound'
    )
    CueSound.setVolume(1.0)

    def play_cue_sound():

        CueSound.play()

    def make_trial_cue_sound(cueFile, name='trialCueSound'):

        trialSound = make_lab_sound(
            cueFile,
            secs=-1,
            stereo=True,
            hamming=True,
            name=name
        )
        trialSound.setVolume(1.0)
        return trialSound
    circle_click1 = visual.ShapeStim(
        win=win, name='circle_click1',
        size=[0.035,0.035], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=0.0, interpolate=True)
    circle_click2 = visual.ShapeStim(
        win=win, name='circle_click2',
        size=[0.0175,0.0175], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=-1.0, interpolate=True)
    click_ = visual.TextStim(win=win, name='click_',
        text='+',
        font='Arial Bold',
        pos=[0,0], height=0.035, wrapWidth=None, ori=0.0,
        color='white', colorSpace='rgb', opacity=None,
        depth=-2.0);
    ClickSound = make_lab_sound(
        'A',
        secs=-1,
        stereo=True,
        hamming=True,
        name='ClickSound'
    )
    ClickSound.setVolume(1.0)

    totalEarned = 0
    visualPracticePenaltyPence = 0
    eyePracticePenaltyPence = 0
    circle_ITI1 = visual.ShapeStim(
        win=win, name='circle_ITI1',
        size=[0.035,0.035], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=0.0, interpolate=True)
    circle_ITI2 = visual.ShapeStim(
        win=win, name='circle_ITI2',
        size=[0.0175,0.0175], vertices='circle',
        ori=0.0, pos=[0,0],
        lineWidth=2.5,
        colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, depth=-1.0, interpolate=True)
    ITI_ = visual.TextStim(win=win, name='ITI_',
        text='',
        font='Arial Bold',
        pos=[0,0], height=0.035, wrapWidth=None, ori=0.0,
        color='white', colorSpace='rgb', opacity=None,
        depth=-2.0);


    if globalClock is None:
        globalClock = core.Clock()
    if isinstance(globalClock, str):
        if globalClock == 'float':
            globalClock = core.Clock(format='float')
        elif globalClock == 'iso':
            globalClock = core.Clock(format='%Y-%m-%d_%H:%M:%S.%f%z')
        else:
            globalClock = core.Clock(format=globalClock)
    if ioServer is not None and hasattr(ioServer, 'syncClock'):
        ioServer.syncClock(globalClock)
    logging.setDefaultClock(globalClock)
    routineTimer = core.Clock()
    win.flip()
    expInfo['expStart'] = data.getDateStr(
        format='%Y-%m-%d %Hh%M.%S.%f %z'
    )


    gazeMouse = event.Mouse(win=win)
    gazeMouse.setVisible(bool(SHOW_MOUSE_CURSOR_DURING_EYETRACKING or EYETRACKER_BACKEND.lower() == 'mousegaze'))

    responseKeyboard = keyboard.Keyboard(clock=globalClock)

    def clear_response_key_events():
        try:
            responseKeyboard.clearEvents()
        except Exception:
            pass

    def get_response_keypresses():

        try:
            return responseKeyboard.getKeys(
                keyList=[responseKey], waitRelease=False, clear=True
            )
        except Exception:
            return []

    def press_global_time(key_event):

        for attr in ('rt', 'tDown'):
            try:
                value = getattr(key_event, attr)
                if value is not None:
                    return float(value)
            except Exception:
                pass
        return float(globalClock.getTime(format='float'))

    def schedule_sound_on_next_flip(sound_obj, event_prefix, visual_marker=True, earliest_ptb=None, **fields):

        try:
            next_flip_ptb = float(win.getFutureFlipTime(clock='ptb'))
        except Exception:
            next_flip_ptb = float('nan')
        try:
            next_flip_global = float(win.getFutureFlipTime(clock=globalClock))
        except Exception:
            next_flip_global = float(globalClock.getTime(format='float'))

        planned_ptb = next_flip_ptb
        if not math.isnan(next_flip_ptb) and earliest_ptb is not None:
            try:
                earliest_value = float(earliest_ptb)
                if not math.isnan(earliest_value):
                    planned_ptb = max(next_flip_ptb, earliest_value)
            except Exception:
                pass

        planned_global = next_flip_global
        if not math.isnan(next_flip_ptb) and not math.isnan(planned_ptb):
            planned_global += max(0.0, planned_ptb - next_flip_ptb)

        scheduled_with_ptb = not math.isnan(planned_ptb)
        try:
            if scheduled_with_ptb:
                sound_obj.play(when=planned_ptb)
            else:
                sound_obj.play()
        except Exception:
            scheduled_with_ptb = False
            sound_obj.play()

        timing = {
            'visual_onset_global': '',
            'audio_planned_onset_global': planned_global,
            'audio_planned_onset_ptb': planned_ptb,
            'audio_scheduled_with_ptb': scheduled_with_ptb,
        }

        def _on_flip():
            visual_onset = float(globalClock.getTime(format='float'))
            timing['visual_onset_global'] = visual_onset
            marker_fields = dict(fields)
            marker_fields.update({
                'plannedAudioGlobal': f'{planned_global:.6f}',
                'plannedAudioPTB': f'{planned_ptb:.6f}',
                'scheduledPTB': int(scheduled_with_ptb),
            })
            if visual_marker:
                tracker_event(event_prefix + '_visual_onset', **marker_fields)
            tracker_event(event_prefix + '_audio_planned_onset', **marker_fields)

        win.callOnFlip(_on_flip)
        return timing

    def mark_visual_on_next_flip(event_name, **fields):

        timing = {'visual_onset_global': ''}

        def _on_flip():
            onset = float(globalClock.getTime(format='float'))
            timing['visual_onset_global'] = onset
            tracker_event(event_name, **fields)

        win.callOnFlip(_on_flip)
        return timing

    def start_phase_on_next_flip(event_name, **fields):

        timing = {'onset_global': ''}

        def _on_flip():
            routineTimer.reset()
            onset = float(globalClock.getTime(format='float'))
            timing['onset_global'] = onset
            tracker_event(event_name, **fields)

        win.callOnFlip(_on_flip)
        return timing

    def send_tracker_message(message):

        tracker = get_eyetracker()
        try:
            if ioServer is not None:
                ioServer.sendMessageEvent(text=str(message))
        except Exception:
            pass
        try:
            if tracker is not None and hasattr(tracker, 'sendMessage'):
                tracker.sendMessage(str(message))
        except Exception:
            pass

    def tracker_event(event_name, **fields):

        event_time = globalClock.getTime(format='float')
        parts = [f"EVENT={event_name}", f"time={event_time:.6f}"]
        for key, value in fields.items():
            safe_value = str(value).replace(' ', '_')
            parts.append(f"{key}={safe_value}")
        message = " ".join(parts)
        send_tracker_message(message)
        write_task_event_record(event_name, event_time, fields)
        return event_time

    def reset_display_timing_log():

        try:
            win.frameIntervals = []
            win.recordFrameIntervals = True
        except Exception:
            pass

    def save_display_timing_summary(label):

        try:
            intervals = list(getattr(win, 'frameIntervals', []))
        except Exception:
            intervals = []
        try:
            refresh_threshold = float(getattr(win, 'refreshThreshold', 1.5 * frameDur))
        except Exception:
            refresh_threshold = 1.5 * frameDur
        dropped = [interval for interval in intervals if interval > refresh_threshold]
        summary = {
            'n_intervals': len(intervals),
            'n_dropped': len(dropped),
            'dropped_proportion': (len(dropped) / len(intervals)) if intervals else '',
            'longest_interval_s': max(intervals) if intervals else '',
            'mean_interval_s': (sum(intervals) / len(intervals)) if intervals else '',
            'refresh_threshold_s': refresh_threshold,
        }
        for key, value in summary.items():
            thisExp.addData(f'display_{label}_{key}', value)
        thisExp.addData(f'display_{label}_measured_refresh_hz', expInfo.get('frameRate_measuredHz', ''))
        thisExp.addData(f'display_{label}_monitor_profile', expInfo.get('monitor_profile', ''))
        thisExp.nextEntry()
        return summary


    POST_CALIBRATION_GREY_SCREEN_DURATION = 4.0
    POST_CALIBRATION_GREY_SCREEN_COLOR = [0, 0, 0]

    def show_post_calibration_grey_screen(label):

        old_color = list(getattr(win, 'color', POST_CALIBRATION_GREY_SCREEN_COLOR))
        old_mouse_visible = getattr(win, 'mouseVisible', False)
        greyClock = core.Clock()

        try:
            win.color = POST_CALIBRATION_GREY_SCREEN_COLOR
            win.mouseVisible = False
            tracker_event(
                'post_calibration_grey_screen_start',
                label=label,
                duration=POST_CALIBRATION_GREY_SCREEN_DURATION
            )

            while greyClock.getTime() < POST_CALIBRATION_GREY_SCREEN_DURATION:
                if vk_down(0x1B):
                    tracker_event('post_calibration_grey_screen_cancelled', label=label)
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return False
                win.flip()

            tracker_event('post_calibration_grey_screen_end', label=label)
            thisExp.addData(f'postCalibrationGreyScreen_{label}_duration', POST_CALIBRATION_GREY_SCREEN_DURATION)
            thisExp.addData(f'postCalibrationGreyScreen_{label}_completed', True)
            thisExp.nextEntry()
            return True
        finally:
            try:
                win.color = old_color
            except Exception:
                pass
            try:
                win.mouseVisible = old_mouse_visible
            except Exception:
                pass
            try:
                win.flip()
            except Exception:
                pass



    lastGazeCoordinateSample = {
        'source': 'missing',
        'mode': 'missing',
        'iohubUnit': '',
        'rawX': None,
        'rawY': None,
        'heightX': None,
        'heightY': None,
    }

    def get_raw_gaze_position():

        tracker = get_eyetracker()

        if tracker is not None:
            try:
                pos = tracker.getLastGazePosition()
                if pos is not None:
                    return pos, 'iohub'
            except Exception:
                pass

            try:
                sample = tracker.getLastSample()
                if sample is not None:
                    for attrName in ['gaze_position', 'left_gaze_position', 'right_gaze_position']:
                        if hasattr(sample, attrName):
                            pos = getattr(sample, attrName)
                            if pos is not None:
                                return pos, 'iohub'
            except Exception:
                pass

        if EYETRACKER_BACKEND.lower() == 'mousegaze':
            try:
                return gazeMouse.getPos(), 'mousegaze'
            except Exception:
                return None, 'missing'

        return None, 'missing'

    def get_iohub_display_coordinate_unit():

        io = deviceManager.ioServer
        display = None
        try:
            display = io.devices.display if io is not None else None
        except Exception:
            display = None

        candidates = []
        if display is not None:
            for methodName in ['getCoordinateType', 'getCoordinateUnitType', 'getCoordinateUnits']:
                try:
                    method = getattr(display, methodName)
                    candidates.append(method())
                except Exception:
                    pass
            for attrName in ['coordinate_type', 'coordinateType', 'coordinate_unit_type', 'coordinateUnitType', 'reporting_unit_type', 'reportingUnitType', 'unit_type', 'unitType', 'units']:
                try:
                    candidates.append(getattr(display, attrName))
                except Exception:
                    pass
            try:
                displayConfig = display.getConfiguration()
                if isinstance(displayConfig, dict):
                    for key in ['coordinate_type', 'coordinateType', 'coordinate_unit_type', 'coordinateUnitType', 'reporting_unit_type', 'reportingUnitType', 'unit_type', 'unitType', 'units']:
                        if key in displayConfig:
                            candidates.append(displayConfig[key])
            except Exception:
                pass

        for value in candidates:
            if value is None:
                continue
            unit = str(value).strip().lower()
            if unit:
                return unit

        return IOHUB_GAZE_UNKNOWN_UNIT_FALLBACK


    IOHUB_GAZE_COORDINATE_UNIT = get_iohub_display_coordinate_unit()
    try:
        thisExp.extraInfo['gaze_coordinate_policy'] = (
            'iohub_display_units_cached_once; explicit_pix_fallback; '
            'mousegaze_height_units'
        )
        thisExp.extraInfo['iohub_display_coordinate_unit_cached'] = IOHUB_GAZE_COORDINATE_UNIT
    except Exception:
        pass

    def gaze_position_in_height_units():

        pos, source = get_raw_gaze_position()
        if pos is None:
            lastGazeCoordinateSample.update({
                'source': source,
                'mode': 'missing',
                'iohubUnit': '',
                'rawX': None,
                'rawY': None,
                'heightX': None,
                'heightY': None,
            })
            return None

        try:
            x, y = float(pos[0]), float(pos[1])
        except Exception:
            lastGazeCoordinateSample.update({
                'source': source,
                'mode': 'invalid_sample',
                'iohubUnit': '',
                'rawX': None,
                'rawY': None,
                'heightX': None,
                'heightY': None,
            })
            return None

        if not np.isfinite(x) or not np.isfinite(y):
            lastGazeCoordinateSample.update({
                'source': source,
                'mode': 'missing_nonfinite',
                'iohubUnit': '',
                'rawX': x,
                'rawY': y,
                'heightX': None,
                'heightY': None,
            })
            return None

        try:
            winW, winH = float(win.size[0]), float(win.size[1])
        except Exception:
            winW, winH = 1024.0, 768.0

        if source == 'mousegaze':
            heightX, heightY = x, y
            coordinateUnit = 'height'
            mode = 'mousegaze_height'
        else:
            coordinateUnit = IOHUB_GAZE_COORDINATE_UNIT
            compactUnit = coordinateUnit.replace('_', '').replace('-', '').replace(' ', '')

            if compactUnit in ['pix', 'pixel', 'pixels']:
                heightX, heightY = x / winH, y / winH
                mode = 'iohub_display_pix_centre'
            elif compactUnit in ['height', 'heightunits']:
                heightX, heightY = x, y
                mode = 'iohub_display_height'
            elif compactUnit in ['norm', 'normalized', 'normalised']:
                heightX = x * (winW / (2.0 * winH))
                heightY = y / 2.0
                mode = 'iohub_display_norm'
            else:
                heightX, heightY = x / winH, y / winH
                mode = f'iohub_display_{coordinateUnit}_assumed_pix'

        lastGazeCoordinateSample.update({
            'source': source,
            'mode': mode,
            'iohubUnit': coordinateUnit,
            'rawX': x,
            'rawY': y,
            'heightX': heightX,
            'heightY': heightY,
        })
        return heightX, heightY

    def gaze_centre_status():

        pos = gaze_position_in_height_units()
        if pos is None:
            return 'missing', None

        x, y = pos
        distance = math.sqrt((float(x) ** 2) + (float(y) ** 2))
        if distance > GAZE_BOUNDARY_RADIUS:
            return 'outside', distance
        return 'inside', distance

    def gaze_is_outside_outer_ring():

        status, _ = gaze_centre_status()
        return status != 'inside'

    def new_gaze_break_monitor():

        return {
            'outsideStartedGlobal': None,
            'outsideStartedLocal': None,
            'lastStatus': None,
            'lastDistance': None,
            'lastOutsideDuration': 0.0,
        }

    def sustained_gaze_break(monitor):

        status, distance = gaze_centre_status()
        nowGlobal = globalClock.getTime(format='float')
        nowLocal = routineTimer.getTime()

        monitor['lastStatus'] = status
        monitor['lastDistance'] = distance

        if status == 'outside':
            if monitor['outsideStartedGlobal'] is None:
                monitor['outsideStartedGlobal'] = nowGlobal
                monitor['outsideStartedLocal'] = nowLocal
                monitor['lastOutsideDuration'] = 0.0
                return False

            outsideDuration = nowGlobal - monitor['outsideStartedGlobal']
            monitor['lastOutsideDuration'] = outsideDuration
            return outsideDuration >= GAZE_BREAK_MIN_DURATION

        monitor['outsideStartedGlobal'] = None
        monitor['outsideStartedLocal'] = None
        monitor['lastOutsideDuration'] = 0.0
        return False

    def log_sustained_gaze_break(prefix, monitor, phase, blockNum=None, trialNum=None):

        thisExp.addData(f'{prefix}_gazeBreak_minDurationRequired', GAZE_BREAK_MIN_DURATION)
        thisExp.addData(f'{prefix}_gazeBreak_outsideDuration', monitor.get('lastOutsideDuration'))
        if blockNum is not None:
            thisExp.addData(f'{prefix}_gazeBreak_block', blockNum)
        if trialNum is not None:
            thisExp.addData(f'{prefix}_gazeBreak_trial', trialNum)
        thisExp.addData(f'{prefix}_gazeBreak_phase', phase)
        thisExp.addData(f'{prefix}_gazeBreak_coordinateSource', lastGazeCoordinateSample.get('source'))
        thisExp.addData(f'{prefix}_gazeBreak_coordinateMode', lastGazeCoordinateSample.get('mode'))
        thisExp.addData(f'{prefix}_gazeBreak_iohubCoordinateUnit', lastGazeCoordinateSample.get('iohubUnit'))
        thisExp.addData(f'{prefix}_gazeBreak_rawGazeX', lastGazeCoordinateSample.get('rawX'))
        thisExp.addData(f'{prefix}_gazeBreak_rawGazeY', lastGazeCoordinateSample.get('rawY'))
        thisExp.addData(f'{prefix}_gazeBreak_heightGazeX', lastGazeCoordinateSample.get('heightX'))
        thisExp.addData(f'{prefix}_gazeBreak_heightGazeY', lastGazeCoordinateSample.get('heightY'))
        tracker_event(
            'gaze_break_coordinate',
            task=prefix,
            phase=phase,
            source=lastGazeCoordinateSample.get('source'),
            mode=lastGazeCoordinateSample.get('mode'),
            rawX=lastGazeCoordinateSample.get('rawX'),
            rawY=lastGazeCoordinateSample.get('rawY'),
            heightX=lastGazeCoordinateSample.get('heightX'),
            heightY=lastGazeCoordinateSample.get('heightY'),
        )

    def wait_for_gaze_to_start_trial(taskLabel, blockNum=None, trialNum=None):

        showWaitPrompt = (taskLabel != 'main')

        waitText = visual.TextStim(
            win=win,
            name='waitForGazeStartText',
            text='Look at the middle of the screen to start the round.',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        stableRequired = 0.20
        stableClock = core.Clock()
        waitClock = core.Clock()
        stableStarted = False
        fixationVisualTiming = None

        while True:
            inside = not gaze_is_outside_outer_ring()

            if inside:
                if not stableStarted:
                    stableClock.reset()
                    stableStarted = True

                if stableClock.getTime() >= stableRequired:
                    thisExp.addData(f'{taskLabel}_gazeWait_block', blockNum)
                    thisExp.addData(f'{taskLabel}_gazeWait_trial', trialNum)
                    thisExp.addData(f'{taskLabel}_gazeWait_duration', waitClock.getTime())
                    thisExp.addData(f'{taskLabel}_gazeWait_completed', True)
                    thisExp.addData(f'{taskLabel}_gazeWait_forceStarted', False)
                    thisExp.addData(f'{taskLabel}_gazeWait_fixationVisualOnsetGlobal', fixationVisualTiming['visual_onset_global'] if fixationVisualTiming else '')
                    thisExp.nextEntry()
                    routineTimer.reset()
                    return True
            else:
                stableStarted = False

            circle_fix1.draw()
            circle_fix2.draw()
            fix_.draw()
            if fixationVisualTiming is None:
                fixationVisualTiming = mark_visual_on_next_flip(
                    f'{taskLabel}_gaze_wait_fixation_visual_onset',
                    block=blockNum,
                    trial=trialNum,
                )
            if showWaitPrompt:
                waitText.draw()
            if EYETRACKER_BACKEND.lower() == 'mousegaze' and taskLabel == 'main' and vk_down(0x20):
                thisExp.addData(f'{taskLabel}_gazeWait_block', blockNum)
                thisExp.addData(f'{taskLabel}_gazeWait_trial', trialNum)
                thisExp.addData(f'{taskLabel}_gazeWait_duration', waitClock.getTime())
                thisExp.addData(f'{taskLabel}_gazeWait_completed', True)
                thisExp.addData(f'{taskLabel}_gazeWait_forceStarted', True)
                thisExp.addData(f'{taskLabel}_gazeWait_fixationVisualOnsetGlobal', fixationVisualTiming['visual_onset_global'] if fixationVisualTiming else '')
                thisExp.nextEntry()
                routineTimer.reset()
                return True

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return None

            win.flip()

    def log_gaze_break(blockNum, trialNum, phase):
        thisExp.addData('gazeBreak_block', blockNum)
        thisExp.addData('gazeBreak_trial', trialNum)
        thisExp.addData('gazeBreak_phase', phase)
        thisExp.addData('gazeBreak_time', globalClock.getTime(format='float'))
        thisExp.nextEntry()
        tracker_event("main_gaze_break", block=blockNum, trial=trialNum, phase=phase)
    def handle_formal_gaze_break(blockNum, trialNum, phase):
        thisExp.addData('main_gazeBreak_action', 'restart_without_recalibration')
        thisExp.addData('main_gazeBreak_recalibrationTriggered', False)
        log_gaze_break(blockNum, trialNum, phase)

        try:
            ClickSound.stop()
        except Exception:
            pass

        gazePrompt = visual.TextStim(
            win=win,
            name='mainGazeBreakPrompt',
            text='Please keep looking at the centre of the screen.',
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        tracker_event(
            "main_gaze_break_prompt_start",
            block=blockNum,
            trial=trialNum,
            phase=phase
        )
        routineTimer.reset()
        while routineTimer.getTime() < 1.5:
            gazePrompt.draw()
            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        tracker_event(
            "main_gaze_break_prompt_end",
            block=blockNum,
            trial=trialNum,
            phase=phase
        )
        routineTimer.reset()
        return True
    instrpratice = data.Routine(
        name='instrpratice',
        components=[instr, startspace],
    )
    instrpratice.status = NOT_STARTED
    continueRoutine = True
    startspace.keys = []
    startspace.rt = []
    _startspace_allKeys = []
    startspaceXWasDown = vk_down(VK_X)
    startspaceMWasDown = vk_down(VK_M)
    instrpratice.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    instrpratice.tStart = globalClock.getTime(format='float')
    instrpratice.status = STARTED
    thisExp.addData('instrpratice.started', instrpratice.tStart)
    instrpratice.maxDuration = None
    instrpraticeComponents = instrpratice.components
    for thisComponent in instrpratice.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    thisExp.currentRoutine = instrpratice
    instrpratice.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine:
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1


        if instr.status == NOT_STARTED and tThisFlip >= 0-frameTolerance:
            instr.frameNStart = frameN
            instr.tStart = t
            instr.tStartRefresh = tThisFlipGlobal
            win.timeOnFlip(instr, 'tStartRefresh')
            thisExp.timestampOnFlip(win, 'instr.started') if hasattr(thisExp, 'timestampOnFlip') else None
            instr.status = STARTED
            instr.setAutoDraw(True)

        if instr.status == STARTED:
            pass

        waitOnFlip = False

        if startspace.status == NOT_STARTED and tThisFlip >= 0-frameTolerance:
            startspace.frameNStart = frameN
            startspace.tStart = t
            startspace.tStartRefresh = tThisFlipGlobal
            win.timeOnFlip(startspace, 'tStartRefresh')
            thisExp.timestampOnFlip(win, 'startspace.started') if hasattr(thisExp, 'timestampOnFlip') else None
            startspace.status = STARTED
            waitOnFlip = True
            win.callOnFlip(startspace.clock.reset)
            win.callOnFlip(startspace.clearEvents, eventType='keyboard')
        if startspace.status == STARTED and not waitOnFlip:
            xDown = vk_down(VK_X)
            mDown = vk_down(VK_M)
            if xDown and not startspaceXWasDown:
                startspace.keys = 'x'
                startspace.rt = startspace.clock.getTime() if hasattr(startspace, 'clock') else t
                startspace.duration = None
                continueRoutine = False
            elif mDown and not startspaceMWasDown:
                startspace.keys = 'm'
                startspace.rt = startspace.clock.getTime() if hasattr(startspace, 'clock') else t
                startspace.duration = None
                continueRoutine = False
            startspaceXWasDown = xDown
            startspaceMWasDown = mDown

        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp,
                win=win,
                timers=[routineTimer, globalClock],
                currentRoutine=instrpratice,
            )
            continue

        if not continueRoutine:
            instrpratice.forceEnded = routineForceEnded = True
        if instrpratice.forceEnded or routineForceEnded:
            break

        if continueRoutine:
            win.flip()
    for thisComponent in instrpratice.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    instrpratice.tStop = globalClock.getTime(format='float')
    instrpratice.tStopRefresh = tThisFlipGlobal
    thisExp.addData('instrpratice.stopped', instrpratice.tStop)
    if startspace.keys in ['', [], None]:
        startspace.keys = None
    thisExp.addData('startspace.keys',startspace.keys)
    if startspace.keys != None:
        thisExp.addData('startspace.rt', startspace.rt)
        thisExp.addData('startspace.duration', startspace.duration)

    if startspace.keys == 'x':
        handedness = 'left'
        responseKey = 'x'
        responseKeyCode = pyglet_key.X
        responseVKCode = VK_X
        holdKeys = ['f', 't', 'h']
        holdKeyCodes = [pyglet_key.F, pyglet_key.T, pyglet_key.H]
        holdVKCodes = [VK_F, VK_T, VK_H]

    elif startspace.keys == 'm':
        handedness = 'right'
        responseKey = 'm'
        responseKeyCode = pyglet_key.M
        responseVKCode = VK_M
        holdKeys = ['f', 't', 'h']
        holdKeyCodes = [pyglet_key.F, pyglet_key.T, pyglet_key.H]
        holdVKCodes = [VK_F, VK_T, VK_H]

    else:
        handedness = 'unknown'
        responseKey = 'x'
        responseKeyCode = pyglet_key.X
        responseVKCode = VK_X
        holdKeys = ['f', 't', 'h']
        holdKeyCodes = [pyglet_key.F, pyglet_key.T, pyglet_key.H]
        holdVKCodes = [VK_F, VK_T, VK_H]

    thisExp.addData('handedness', handedness)
    thisExp.addData('responseKey', responseKey)
    thisExp.addData('holdKeys', ",".join(holdKeys))
    thisExp.addData('responseKeyCode', responseKeyCode)
    thisExp.addData('holdKeyCodes', ",".join(str(code) for code in holdKeyCodes))
    thisExp.addData('responseVKCode', responseVKCode)
    thisExp.addData('holdVKCodes', ",".join(str(code) for code in holdVKCodes))

    thisExp.nextEntry()

    continueLabel = 'X' if responseKey == 'x' else 'M'

    routineTimer.reset()

    if RUN_HAND_SETUP_INSTRUCTION:
        if handedness == 'left':
            handInstrText = (
                "Place your fingers on the marked F, T, and H keys.\n\n"
                "Keep these three keys held down throughout the task.\n\n"
                "While holding them, use your left little finger to press X to continue."
            )
        else:
            handInstrText = (
                "Place your fingers on the marked F, T, and H keys.\n\n"
                "Keep these three keys held down throughout the task.\n\n"
                "While holding them, use your right little finger to press M to continue."
            )

        handInstr = visual.TextStim(
            win=win,
            name='handInstr',
            text=handInstrText,
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        handContinueText = visual.TextStim(
            win=win,
            name='handContinueText',
            text='',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        handKey = keyboard.Keyboard()
        handKey.keys = None
        handKey.rt = None

        continueRoutine = True
        routineTimer.reset()
        t = 0
        frameN = -1

        handResponseWasDown = vk_down(responseVKCode)

        while continueRoutine:
                t = routineTimer.getTime()
                frameN += 1

                holdOK = hold_keys_ok(holdVKCodes)
                responseDown = vk_down(responseVKCode)

                handInstr.draw()

                if holdOK:
                    handContinueText.setText(f"Press {continueLabel} to continue.")
                else:
                    handContinueText.setText("Keep holding the three marked keys.")
                handContinueText.draw()

                if responseDown and not handResponseWasDown:
                    if holdOK:
                        handKey.keys = responseKey
                        handKey.rt = t
                        continueRoutine = False

                handResponseWasDown = responseDown

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return

                win.flip()

        thisExp.addData('handInstruction.keys', handKey.keys)
        thisExp.addData('handInstruction.rt', handKey.rt)
        thisExp.nextEntry()
        routineTimer.reset()



    MAIN_CUE_IDENTITIES = (1, 2, 3, 4, 5, 6)
    CUE_PREVIEW_VERSION = 13
    EYE_PRACTICE_CUE_VERSION = 14
    MAIN_N_CONDITIONS = 6
    MAIN_N_BLOCKS = 12
    MAIN_TRIALS_PER_BLOCK = 6
    MAIN_REST_AFTER_BLOCKS = [4, 8]
    MAIN_CUE_BLOCK_VERSIONS = list(range(1, 13))
    VISUAL_PRACTICE_CUE_IDENTITY = 10

    CUE_IDENTITY_LABELS = {
        1: "Bird",
        2: "Bubble",
        3: "Fire",
        4: "Laundry",
        5: "Writing",
        6: "Typing",
        10: "Thunder",
    }
    CUE_IDENTITY_FILE_LABELS = {
        1: [(1, "bird")],
        2: [(2, "bubble")],
        3: [(3, "fire")],
        4: [(4, "luandry")],
        5: [(5, "writing")],
        6: [(6, "typing")],
        10: [(10, "thunder")],
    }
    CUE_IDENTITY_IMAGE_LABELS = {
        1: ["bird"],
        2: ["bubble"],
        3: ["fire"],
        4: ["luandry", "laundry"],
        5: ["writing"],
        6: ["typing"],
        10: ["thunder"],
    }

    def cue_identity_from_file(cueFile):

        parsed = _parse_numbered_cue_file(cueFile)
        if parsed is None:
            return None
        fileIdentity, label, _version = parsed
        labelLower = str(label).lower()
        for logicalIdentity, fileLabels in CUE_IDENTITY_FILE_LABELS.items():
            for fileIdentityExpected, fileLabelExpected in fileLabels:
                if fileIdentity != int(fileIdentityExpected):
                    continue
                if fileLabelExpected is not None and str(fileLabelExpected).lower() not in labelLower:
                    continue
                return logicalIdentity
        return fileIdentity

    def _normalise_audio_path(path):

        if path is None:
            return None
        try:
            path = os.path.normpath(path)
            if os.path.dirname(path) == '':
                return path
            return path
        except Exception:
            return path

    def _scan_audio_files():

        searchRoots = [baseDir]
        for relRoot in [
            'stimuli',
            'stimuli_eq',
            os.path.join('cue_sound_processing', 'stimuli'),
            os.path.join('cue_sound_processing', 'stimuli_eq'),
            os.path.join('equalize_stimuli', 'cue_sound_processing', 'stimuli_eq'),
        ]:
            fullRoot = os.path.join(baseDir, relRoot)
            if os.path.isdir(fullRoot):
                searchRoots.append(fullRoot)

        found = []
        seen = set()
        for root in searchRoots:
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames if d.lower() not in ['data', '.git', '__pycache__']]
                    for f in filenames:
                        if f.lower().endswith(('.wav', '.mp3', '.ogg')):
                            fullPath = os.path.normpath(os.path.join(dirpath, f))
                            key = fullPath.lower()
                            if key not in seen:
                                found.append(fullPath)
                                seen.add(key)
            except Exception:
                pass
        return found

    AUDIO_FILES_ALL = _scan_audio_files()
    AUDIO_FILE_BY_BASENAME = {}
    for audioPath in AUDIO_FILES_ALL:
        AUDIO_FILE_BY_BASENAME.setdefault(os.path.basename(audioPath).lower(), audioPath)

    def resolve_audio_file(filename_or_path):

        if filename_or_path is None:
            return filename_or_path
        f = str(filename_or_path)
        if os.path.exists(f):
            return _normalise_audio_path(f)
        direct = os.path.join(baseDir, f)
        if os.path.exists(direct):
            return _normalise_audio_path(direct)
        byBase = AUDIO_FILE_BY_BASENAME.get(os.path.basename(f).lower())
        if byBase:
            return _normalise_audio_path(byBase)
        return f

    def resolve_reward_file(filename_or_path):

        if filename_or_path is None:
            return filename_or_path
        return resolve_audio_file(str(filename_or_path))


    def _parse_numbered_cue_file(path):

        base = os.path.basename(str(path))
        m = re.match(r"^(\d+)(.*?)(?:_v(\d+))?\.(wav|mp3|ogg)$", base, re.IGNORECASE)
        if not m:
            return None
        cueIdentity = int(m.group(1))
        label = m.group(2).strip('_- ')
        version = int(m.group(3)) if m.group(3) is not None else None
        return cueIdentity, label, version

    def get_cue_file_by_identity_and_version(cueIdentity, version=None):

        logicalIdentity = int(cueIdentity)
        fileLabels = CUE_IDENTITY_FILE_LABELS.get(logicalIdentity, [(logicalIdentity, None)])
        exactMatches = []

        for path in AUDIO_FILES_ALL:
            parsed = _parse_numbered_cue_file(path)
            if parsed is None:
                continue
            fileIdentity, label, fileVersion = parsed
            labelLower = str(label).lower()

            matchPriority = None
            for priorityIndex, fileLabel in enumerate(fileLabels):
                fileIdentityExpected, fileLabelExpected = fileLabel
                if fileIdentity != int(fileIdentityExpected):
                    continue
                if fileLabelExpected is not None and str(fileLabelExpected).lower() not in labelLower:
                    continue
                matchPriority = priorityIndex
                break
            if matchPriority is None:
                continue

            item = (matchPriority, path)
            if version is not None and fileVersion == int(version):
                exactMatches.append(item)
            elif version is None:
                exactMatches.append(item)

        if exactMatches:
            return resolve_audio_file(sorted(exactMatches)[0][1])
        return None

    def get_main_cue_files_by_identity_and_block():






        cueFiles = {}
        missing = []

        for cueIdentity in range(1, MAIN_N_CONDITIONS + 1):
            for blockNum in MAIN_CUE_BLOCK_VERSIONS:
                f = get_cue_file_by_identity_and_version(cueIdentity, blockNum)
                if f is None:
                    missing.append(f"cue {cueIdentity}, block v{blockNum:02d}")
                else:
                    cueFiles[(cueIdentity, blockNum)] = f

        if len(missing) > 0:
            errorText = visual.TextStim(
                win=win,
                name='mainCueMissingErrorEarly',
                text=(
                    "Some formal cue sound files are missing.\n\n"
                    "This task uses six cue identities, one for each reward-effort condition.\n"
                    "Please check that cues 1-6 each have v01-v12 files."
                ),
                font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
            )
            routineTimer.reset()
            while routineTimer.getTime() < 5.0:
                errorText.draw()
                win.flip()
            raise RuntimeError("Missing main-task v01-v12 cue files.")
        else:
            thisExp.addData("mainCueFilesLoaded", True)
            thisExp.nextEntry()

        return cueFiles

    def get_preview_cue_file(cueIdentity):

        previewFile = get_cue_file_by_identity_and_version(cueIdentity, CUE_PREVIEW_VERSION)
        if previewFile is None:
            raise RuntimeError(f"Missing preview cue file for cue {cueIdentity}, v{CUE_PREVIEW_VERSION:02d}")
        return previewFile

    def make_main_condition_rows():





        conditionSpecs = [
            (1, 1),
            (1, 5),
            (1, 10),
            (5, 1),
            (5, 5),
            (5, 10),
        ]
        rows = []
        for conditionIndex, (magValue, frValue) in enumerate(conditionSpecs):
            rows.append({
                'mag': magValue,
                'FR': frValue,
                'fbFile': resolve_reward_file(f"{int(magValue)}pclickres.wav"),
                'conditionLabel': f"{int(magValue)}p_FR{int(frValue)}",
                'rewardPerPress': float(magValue) / float(frValue),
                'conditionIndex': conditionIndex,
            })
        return rows

    mainConditionFile = "task_conditions_1p_5p_FR1_FR5_FR10"
    mainConditionRows = make_main_condition_rows()


    mainCueFiles = get_main_cue_files_by_identity_and_block()

    eyePracticeCueFiles = {}
    missingEyePracticeCues = []
    for cueIdentity in MAIN_CUE_IDENTITIES:
        cueFile = get_cue_file_by_identity_and_version(cueIdentity, EYE_PRACTICE_CUE_VERSION)
        if cueFile is None:
            missingEyePracticeCues.append(f"cue {cueIdentity}, v{EYE_PRACTICE_CUE_VERSION:02d}")
        else:
            eyePracticeCueFiles[cueIdentity] = cueFile

    if missingEyePracticeCues:
        raise RuntimeError(
            "Missing eye-tracking practice cue files: " + ", ".join(missingEyePracticeCues)
        )

    participantIDForSeed = str(expInfo.get("participant", "0"))
    try:
        participantSeed = int(participantIDForSeed)
    except Exception:
        participantSeed = sum(ord(ch) for ch in participantIDForSeed)

    def make_latin_square_cue_mapping(participantNumber, nConditions=6):











        try:
            participantNumber = int(participantNumber)
        except Exception:
            participantNumber = sum(ord(ch) for ch in str(participantNumber))

        latinSquareRow = (participantNumber - 1) % nConditions
        latinSquareCycle = (participantNumber - 1) // nConditions

        mapping = {}
        for conditionIndex in range(nConditions):
            cueIdentity = ((conditionIndex + latinSquareRow) % nConditions) + 1
            mapping[conditionIndex] = cueIdentity

        return mapping, latinSquareRow + 1, latinSquareCycle + 1

    conditionToCueIdentity, latinSquareRow, latinSquareCycle = make_latin_square_cue_mapping(
        participantSeed,
        nConditions=MAIN_N_CONDITIONS
    )

    participantMappedMainRows = []

    for conditionIndex, conditionRow in enumerate(mainConditionRows):
        cueIdentity = conditionToCueIdentity[conditionIndex]

        mappedRow = dict(conditionRow)
        mappedRow['conditionIndex'] = conditionIndex
        mappedRow['cueIdentity'] = cueIdentity
        mappedRow['cueFile'] = mainCueFiles[(cueIdentity, 1)]
        participantMappedMainRows.append(mappedRow)

    thisExp.addData("mainTask_conditionFile", mainConditionFile)
    thisExp.addData("mainTask_participantSeed", participantSeed)
    thisExp.addData("mainTask_cueAssignmentMethod", "latin_square")
    thisExp.addData("mainTask_latinSquareRow", latinSquareRow)
    thisExp.addData("mainTask_latinSquareCycle", latinSquareCycle)
    thisExp.addData("mainTask_conditionToCueIdentity", str(conditionToCueIdentity))
    thisExp.addData("mainTask_nBlocks", MAIN_N_BLOCKS)
    thisExp.addData("mainTask_trialsPerBlock", MAIN_TRIALS_PER_BLOCK)
    thisExp.addData("mainTask_totalTrials", MAIN_N_BLOCKS * MAIN_TRIALS_PER_BLOCK)
    thisExp.addData("mainTask_restAfterBlocks", str(MAIN_REST_AFTER_BLOCKS))
    thisExp.addData("audio_rewardOverlapEnabled", REWARD_SOUND_OVERLAP_ENABLED)
    thisExp.addData("audio_rewardSoundVolume", REWARD_SOUND_VOLUME)
    thisExp.addData("audio_taskCuePlayback", "until_click_window_end")
    thisExp.nextEntry()



    def get_visual_practice_cue_file():
        for candidate in ('10thunder.wav', '10thunder_v01.wav'):
            resolved = resolve_audio_file(candidate)
            if resolved is not None and os.path.exists(resolved):
                return resolved
        raise RuntimeError('Missing visual-practice thunder cue (10thunder.wav).')

    visualPracticeCueFile = get_visual_practice_cue_file()

    def next_visual_practice_cue_file():
        return visualPracticeCueFile, None

    thisExp.addData("visualPracticeCueIdentity", VISUAL_PRACTICE_CUE_IDENTITY)
    thisExp.addData("visualPracticeCueFile", visualPracticeCueFile)
    thisExp.addData("cuePreviewVersion", CUE_PREVIEW_VERSION)
    thisExp.addData("eyePracticeCueVersion", EYE_PRACTICE_CUE_VERSION)
    thisExp.nextEntry()


    if RUN_CUE_SOUND_PREVIEW:
        previewConditions = participantMappedMainRows
        cuePreviewFiles = []
        for row in previewConditions:
            cuePreviewFiles.append(get_preview_cue_file(row['cueIdentity']))
        thisExp.addData('cuePreview_version', CUE_PREVIEW_VERSION)
        thisExp.nextEntry()

        previewHoldVKCodes = [VK_F, VK_T, VK_H]

        cueIntro = visual.TextStim(
            win=win,
            name='cueIntro',
            text=(
                "You are about to play the piggy bank task again.\n\n"
                "First, you will complete a short practice round.\n\n"
                "After practice, the piggy banks will no longer be shown on screen.\n"
                "Instead, each piggy bank will be identified by a different sound. "
                "Listen carefully: sound is the only way to tell the piggy banks apart."
            ),
            font='Arial',
            pos=[0, 0.130],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        cueCounter = visual.TextStim(
            win=win,
            name='cueCounter',
            text='0/6',
            font='Arial',
            pos=[0, -0.235],
            height=TASK_TEXT_HEIGHT,
            color='white',
            colorSpace='rgb'
        )

        cueContinueText = visual.TextStim(
            win=win,
            name='cueContinueText',
            text='',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        def cue_label_from_file(cueFile):
            cueIdentity = cue_identity_from_file(cueFile)
            if cueIdentity in CUE_IDENTITY_LABELS:
                return CUE_IDENTITY_LABELS[cueIdentity]

            stem = os.path.splitext(os.path.basename(str(cueFile)))[0]
            stem = re.sub(r"^[0-9]+", "", stem)
            stem = re.sub(r"_?v[0-9]+$", "", stem, flags=re.IGNORECASE)
            stem = stem.replace("_", " ").replace("-", " ").strip()
            return stem.title() if stem else "Sound"

        def find_cue_image_file(cueFile):
            stem = os.path.splitext(os.path.basename(str(cueFile)))[0]
            stemNoVersion = re.sub(r"_?v[0-9]+$", "", stem, flags=re.IGNORECASE)

            baseNames = []
            cueIdentity = cue_identity_from_file(cueFile)
            if cueIdentity in CUE_IDENTITY_IMAGE_LABELS:
                baseNames.extend(CUE_IDENTITY_IMAGE_LABELS[cueIdentity])

            for base in [stem, stemNoVersion, re.sub(r"^[0-9]+", "", stemNoVersion)]:
                base = base.strip()
                if base:
                    baseNames.append(base)

            candidates = []
            seenCandidates = set()
            imageRoots = [
                baseDir,
                os.path.join(baseDir, "stimuli"),
                os.path.join(baseDir, "stimuli_eq"),
                os.path.join(baseDir, "images"),
                os.path.join(baseDir, "cue_images"),
            ]

            for base in baseNames:
                for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
                    for name in [
                        base + ext,
                        base.lower() + ext,
                        base.title() + ext,
                    ]:
                        key = name.lower()
                        if key not in seenCandidates:
                            candidates.append(name)
                            seenCandidates.add(key)

            for root in imageRoots:
                if not os.path.isdir(root):
                    continue
                for candidate in candidates:
                    path = os.path.join(root, candidate)
                    if os.path.exists(path):
                        return path

            return None

        pageGridPositions = [
            [-0.30, -0.100], [0.00, -0.100], [0.30, -0.100],
        ]

        cuePreviewItems = []
        for cueFile in cuePreviewFiles:
            imagePath = find_cue_image_file(cueFile)
            itemLabel = cue_label_from_file(cueFile)
            cuePreviewItems.append({
                'cueFile': cueFile,
                'imagePath': imagePath,
                'labelText': itemLabel,
            })

        cuePageItems = [cuePreviewItems[0:3], cuePreviewItems[3:6]]

        for pageIndex, pageItems in enumerate(cuePageItems):
            for itemIndex, item in enumerate(pageItems):
                pos = pageGridPositions[itemIndex]
                if item['imagePath'] is not None:
                    imageStim = visual.ImageStim(
                        win=win,
                        name=f'cuePreviewImage_page{pageIndex + 1}_{itemIndex + 1}',
                        image=item['imagePath'],
                        pos=pos,
                        size=[0.22, 0.140],
                        units='height'
                    )
                else:
                    imageStim = None

                boxStim = visual.Rect(
                    win=win,
                    name=f'cuePreviewBox_page{pageIndex + 1}_{itemIndex + 1}',
                    width=0.24,
                    height=0.155,
                    pos=pos,
                    lineWidth=2,
                    lineColor='grey',
                    fillColor=None,
                    colorSpace='named'
                )

                labelStim = visual.TextStim(
                    win=win,
                    name=f'cuePreviewLabel_page{pageIndex + 1}_{itemIndex + 1}',
                    text=item['labelText'],
                    font='Arial',
                    pos=[pos[0], pos[1] - 0.098],
                    height=TASK_TEXT_HEIGHT,
                    wrapWidth=0.24,
                    color='white',
                    colorSpace='rgb'
                )

                item['image'] = imageStim
                item['box'] = boxStim
                item['label'] = labelStim

        cuePreviewSound = make_lab_sound(
            'A',
            secs=5.0,
            stereo=True,
            hamming=True,
            name='cuePreviewSound'
        )
        cuePreviewSound.setVolume(1.0)

        cueIndex = 0
        currentPreviewIndex = None
        waitingToAdvanceCue = False
        continueRoutine = True
        routineTimer.reset()

        previewResponseWasDown = vk_down(responseVKCode)

        while continueRoutine:
            cueCounter.setText(f"{min(cueIndex, len(cuePreviewFiles))}/{len(cuePreviewFiles)}")

            holdStates = [vk_down(k) for k in previewHoldVKCodes]
            holdOK = all(holdStates)
            responseDown = vk_down(responseVKCode)

            if waitingToAdvanceCue:
                currentPageIndex = 1
            elif currentPreviewIndex is not None:
                currentPageIndex = 0 if currentPreviewIndex < 3 else 1
            elif cuePreviewFiles:
                currentPageIndex = 0 if min(cueIndex, len(cuePreviewFiles) - 1) < 3 else 1
            else:
                currentPageIndex = 0
            displayedItems = cuePageItems[currentPageIndex]

            if waitingToAdvanceCue:
                cueContinueText.setText(
                    f"You have heard all 6 sounds.\n\nPress {continueLabel} to continue."
                )
            else:
                if holdOK:
                    cueContinueText.setText(
                        f"Press {continueLabel} to see and hear the next sound."
                    )
                else:
                    cueContinueText.setText("Keep holding the three marked keys.")

            cueIntro.draw()

            for globalIndex, item in enumerate(displayedItems, start=currentPageIndex * 3):
                item['box'].lineColor = 'white' if globalIndex == currentPreviewIndex else 'grey'
                item['box'].draw()
                if item['image'] is not None:
                    item['image'].draw()
                else:
                    cueLabelText = visual.TextStim(
                        win=win,
                        name=f'cuePreviewLabelText_page{currentPageIndex + 1}_{globalIndex + 1}',
                        text=item['label'].text,
                        font='Arial',
                        pos=item['box'].pos,
                        height=TASK_TEXT_HEIGHT,
                        wrapWidth=0.24,
                        color='white',
                        colorSpace='rgb'
                    )
                    cueLabelText.draw()
                item['label'].draw()

            cueCounter.draw()
            cueContinueText.draw()

            if waitingToAdvanceCue and responseDown and not previewResponseWasDown and holdOK:
                cuePreviewSound.stop()
                continueRoutine = False
                continue

            if responseDown and not previewResponseWasDown:
                if holdOK and cueIndex < len(cuePreviewFiles):
                    currentPreviewIndex = cueIndex
                    cuePreviewSound.stop()
                    cuePreviewSound.setSound(cuePreviewFiles[cueIndex], secs=5.0, hamming=True)
                    cuePreviewSound.setVolume(1.0)
                    cuePreviewSound.seek(0)
                    tracker_event(
                        "cue_preview_sound_onset",
                        soundNumber=cueIndex + 1,
                        cueFile=cuePreviewFiles[cueIndex],
                        cueImage=cuePreviewItems[cueIndex]['imagePath']
                    )
                    cuePreviewSound.play()

                    thisExp.addData(f'cuePreview_{cueIndex + 1}_file', cuePreviewFiles[cueIndex])
                    thisExp.addData(f'cuePreview_{cueIndex + 1}_image', cuePreviewItems[cueIndex]['imagePath'])
                    thisExp.addData(f'cuePreview_{cueIndex + 1}_time', globalClock.getTime(format='float'))

                    cueIndex += 1

                    if cueIndex >= len(cuePreviewFiles):
                        waitingToAdvanceCue = True

            previewResponseWasDown = responseDown

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return

            win.flip()

        thisExp.addData('cuePreview.completed', True)
        thisExp.nextEntry()
        routineTimer.reset()


    if RUN_PRESS_FEEDBACK_PREVIEW:
        def get_reward_preview_list_from_prepared_files():
            preview = [
                {'label': '1 penny', 'value': 1, 'file': '1pclickres.wav'},
                {'label': '5 pence', 'value': 5, 'file': '5pclickres.wav'},
            ]
            for item in preview:
                thisExp.addData(f"rewardPreview_{item['label'].replace(' ', '_')}_file", item['file'])
            thisExp.addData('rewardPreview_uses_condition_fbFiles', False)
            return preview

        rewardPreviewList = get_reward_preview_list_from_prepared_files()
        rewardHoldVKCodes = [VK_F, VK_T, VK_H]

        rewardIntro = visual.TextStim(
            win=win,
            name='rewardIntro',
            text=(
                "During the task, you won’t see coins falling. Instead, you will hear them.\n\n"
                "Each piggy bank pays out either 1p or 5p per coin. "
                "The coin sound tells you which."
            ),
            font='Arial', pos=[0, 0.140], height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
        )
        rewardLabelText = visual.TextStim(
            win=win, name='rewardLabelText', text='', font='Arial',
            pos=[0, -0.010], height=TASK_TEXT_HEIGHT, wrapWidth=CENTRAL_TEXT_WRAP,
            color='white', colorSpace='rgb'
        )

        rewardPreviewCoinFiles = {
            1: os.path.join(baseDir, "piggy-banks", "1p-num.png"),
            5: os.path.join(baseDir, "piggy-banks", "5p-num.png"),
        }
        rewardPreviewCoinStims = {}
        for rewardValue, rewardCoinFile in rewardPreviewCoinFiles.items():
            if os.path.exists(rewardCoinFile):
                rewardPreviewCoinStims[rewardValue] = visual.ImageStim(
                    win=win,
                    name=f'rewardPreviewCoin_{rewardValue}p',
                    image=rewardCoinFile,
                    pos=[0, -0.085],
                    size=[0.070, 0.070],
                    units='height'
                )

        rewardCounter = visual.TextStim(
            win=win, name='rewardCounter', text='', font='Arial',
            pos=[0, -0.165], height=TASK_TEXT_HEIGHT,
            color='white', colorSpace='rgb'
        )
        rewardContinueText = visual.TextStim(
            win=win, name='rewardContinueText', text='', font='Arial',
            pos=[0, BOTTOM_PROMPT_Y], height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP, color='white', colorSpace='rgb'
        )
        rewardPreviewSound = make_lab_sound(
            'A', secs=-1, stereo=True, hamming=True, name='rewardPreviewSound'
        )
        rewardPreviewSound.setVolume(1.0)

        rewardSoundIndex = 0
        rewardRepeatIndex = 0
        rewardResponseWasDown = vk_down(responseVKCode)
        waitingToAdvanceReward = False
        continueRoutine = True
        routineTimer.reset()

        while continueRoutine:
            currentReward = rewardPreviewList[rewardSoundIndex]
            rewardLabelText.setText(f"This sound is for {currentReward['label']}.")
            if waitingToAdvanceReward:
                rewardCounter.setText(
                    f"Sound {rewardSoundIndex + 1}/{len(rewardPreviewList)}    Play 5/5"
                )
            else:
                rewardCounter.setText(
                    f"Sound {rewardSoundIndex + 1}/{len(rewardPreviewList)}    Play {rewardRepeatIndex}/5"
                )

            holdOK = hold_keys_ok(rewardHoldVKCodes)
            responseDown = vk_down(responseVKCode)
            if not holdOK:
                rewardContinueText.setText("Keep holding the three marked keys.")
            elif waitingToAdvanceReward and rewardSoundIndex < len(rewardPreviewList) - 1:
                rewardContinueText.setText(f"Press {continueLabel} for the next sound.")
            elif waitingToAdvanceReward:
                rewardContinueText.setText(f"Press {continueLabel} to continue.")
            else:
                rewardContinueText.setText(f"Press {continueLabel} to hear the sound.")

            rewardIntro.draw()
            rewardLabelText.draw()
            rewardCoinStim = rewardPreviewCoinStims.get(int(currentReward['value']))
            if rewardCoinStim is not None:
                rewardCoinStim.draw()
            rewardCounter.draw()
            rewardContinueText.draw()

            if responseDown and not rewardResponseWasDown and holdOK:
                if waitingToAdvanceReward:
                    waitingToAdvanceReward = False
                    rewardRepeatIndex = 0
                    rewardSoundIndex += 1
                    if rewardSoundIndex >= len(rewardPreviewList):
                        continueRoutine = False
                        continue
                elif rewardRepeatIndex < 5:
                    rewardPreviewSound.stop()
                    rewardPreviewSound.setSound(resolve_reward_file(currentReward['file']), hamming=True)
                    rewardPreviewSound.setVolume(1.0)
                    rewardPreviewSound.seek(0)
                    tracker_event(
                        'reward_preview_sound_onset',
                        soundNumber=rewardSoundIndex + 1,
                        repeat=rewardRepeatIndex + 1,
                        rewardFile=currentReward['file'],
                        label=currentReward['label']
                    )
                    rewardPreviewSound.play()
                    thisExp.addData(
                        f"rewardPreview_sound{rewardSoundIndex + 1}_repeat{rewardRepeatIndex + 1}_file",
                        currentReward['file']
                    )
                    thisExp.addData(
                        f"rewardPreview_sound{rewardSoundIndex + 1}_repeat{rewardRepeatIndex + 1}_label",
                        currentReward['label']
                    )
                    thisExp.addData(
                        f"rewardPreview_sound{rewardSoundIndex + 1}_repeat{rewardRepeatIndex + 1}_time",
                        globalClock.getTime(format='float')
                    )
                    rewardRepeatIndex += 1
                    if rewardRepeatIndex >= 5:
                        waitingToAdvanceReward = True

            rewardResponseWasDown = responseDown
            if vk_down(0x1B):
                rewardPreviewSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return
            win.flip()

        rewardPreviewSound.stop()
        thisExp.addData('rewardPreview.completed', True)
        thisExp.nextEntry()
        routineTimer.reset()

        if RUN_COIN_SOUND_TEST:
            coinTestSpaceIsOneP = (int(participantSeed) % 2 == 1)
            if coinTestSpaceIsOneP:
                onePKeyLabel, onePVKCode = 'SPACE', 0x20
                fivePKeyLabel, fivePVKCode = continueLabel, responseVKCode
            else:
                onePKeyLabel, onePVKCode = continueLabel, responseVKCode
                fivePKeyLabel, fivePVKCode = 'SPACE', 0x20

            thisExp.addData('coinSoundTest_enabled', True)
            thisExp.addData('coinSoundTest_nTrialsPerAttempt', 5)
            thisExp.addData('coinSoundTest_usesSingleSoundPerTrial', True)
            thisExp.addData('coinSoundTest_allCorrectRequired', True)
            thisExp.addData('coinSoundTest_1pKey', onePKeyLabel)
            thisExp.addData('coinSoundTest_5pKey', fivePKeyLabel)
            thisExp.addData('coinSoundTest_keyMappingCounterbalance', 'participant_number_odd_even')
            thisExp.nextEntry()

            coinTestIntro = visual.TextStim(
                win=win, name='coinSoundTestIntro',
                text=(
                    "Now you will hear one coin sound at a time.\n\n"
                    "Decide whether it is worth 1p or 5p.\n\n"
                    f"Press {onePKeyLabel} for 1p.\n"
                    f"Press {fivePKeyLabel} for 5p.\n\n"
                    "You need to get all 5 correct to continue.\n\n"
                    "Press SPACE to start."
                ),
                font='Arial', pos=[0, CENTRAL_TEXT_MID_Y],
                height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
            )
            introSpaceWasDown = vk_down(0x20)
            while True:
                spaceDown = vk_down(0x20)
                coinTestIntro.draw()
                if spaceDown and not introSpaceWasDown:
                    break
                introSpaceWasDown = spaceDown
                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return
                win.flip()

            coinTestSound = make_lab_sound(
                'A', secs=-1, stereo=True, hamming=True, name='coinSoundTestSound'
            )
            coinTestSound.setVolume(1.0)
            testAttempt = 0

            while True:
                testAttempt += 1
                testValues = [1, 5, 1, 5, py_random.choice([1, 5])]
                py_random.shuffle(testValues)
                attemptPassed = True

                for testTrialNum, coinValue in enumerate(testValues, start=1):
                    coinFile = '1pclickres.wav' if coinValue == 1 else '5pclickres.wav'
                    listenStim = visual.TextStim(
                        win=win, name='coinSoundTestListenText',
                        text=f"Sound {testTrialNum}/5\n\nListen.",
                        font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                        wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
                    )
                    coinTestSound.stop()
                    coinTestSound.setSound(resolve_reward_file(coinFile), hamming=True)
                    coinTestSound.setVolume(1.0)
                    coinTestSound.seek(0)
                    tracker_event(
                        'coin_sound_test_sound_onset',
                        attempt=testAttempt, trial=testTrialNum, coinFile=coinFile
                    )
                    coinTestSound.play()
                    routineTimer.reset()
                    while routineTimer.getTime() < 0.55:
                        listenStim.draw()
                        if vk_down(0x1B):
                            coinTestSound.stop()
                            thisExp.status = FINISHED
                            endExperiment(thisExp, win=win)
                            return
                        win.flip()
                    coinTestSound.stop()

                    responseStim = visual.TextStim(
                        win=win, name='coinSoundTestResponseText',
                        text=(
                            f"Sound {testTrialNum}/5\n\n"
                            "Was that sound worth 1p or 5p?"
                        ),
                        font='Arial', pos=[0, CENTRAL_TEXT_MID_Y + 0.055], height=TASK_TEXT_HEIGHT,
                        wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
                    )
                    onePOptionStim = visual.TextStim(
                        win=win, name='coinSoundTestOnePOption',
                        text=f"Press {onePKeyLabel} for 1p.",
                        font='Arial', pos=[-0.22, CENTRAL_TEXT_MID_Y - 0.055], height=TASK_TEXT_HEIGHT,
                        wrapWidth=0.4, color='white', colorSpace='rgb'
                    )
                    fivePOptionStim = visual.TextStim(
                        win=win, name='coinSoundTestFivePOption',
                        text=f"Press {fivePKeyLabel} for 5p.",
                        font='Arial', pos=[0.22, CENTRAL_TEXT_MID_Y - 0.055], height=TASK_TEXT_HEIGHT,
                        wrapWidth=0.4, color='white', colorSpace='rgb'
                    )
                    onePWasDown = vk_down(onePVKCode)
                    fivePWasDown = vk_down(fivePVKCode)
                    responseClock = core.Clock()
                    choiceValue = None
                    choiceKey = None
                    choiceRT = None

                    while choiceValue is None:
                        onePDown = vk_down(onePVKCode)
                        fivePDown = vk_down(fivePVKCode)
                        responseStim.draw()
                        onePOptionStim.draw()
                        fivePOptionStim.draw()
                        if onePDown and not onePWasDown:
                            choiceValue = 1
                            choiceKey = onePKeyLabel.lower()
                            choiceRT = responseClock.getTime()
                        elif fivePDown and not fivePWasDown:
                            choiceValue = 5
                            choiceKey = fivePKeyLabel.lower()
                            choiceRT = responseClock.getTime()
                        onePWasDown = onePDown
                        fivePWasDown = fivePDown
                        if vk_down(0x1B):
                            thisExp.status = FINISHED
                            endExperiment(thisExp, win=win)
                            return
                        win.flip()

                    correct = (choiceValue == coinValue)
                    if not correct:
                        attemptPassed = False
                    thisExp.addData('coinSoundTest_attempt', testAttempt)
                    thisExp.addData('coinSoundTest_trial', testTrialNum)
                    thisExp.addData('coinSoundTest_soundFile', coinFile)
                    thisExp.addData('coinSoundTest_correctValue', coinValue)
                    thisExp.addData('coinSoundTest_choiceValue', choiceValue)
                    thisExp.addData('coinSoundTest_choiceKey', choiceKey)
                    thisExp.addData('coinSoundTest_rt', choiceRT)
                    thisExp.addData('coinSoundTest_correct', correct)
                    thisExp.nextEntry()

                    if testTrialNum < len(testValues):
                        routineTimer.reset()
                        while routineTimer.getTime() < 3.0:
                            circle_ITI1.draw()
                            circle_ITI2.draw()
                            if vk_down(0x1B):
                                thisExp.status = FINISHED
                                endExperiment(thisExp, win=win)
                                return
                            win.flip()
                        routineTimer.reset()

                thisExp.addData('coinSoundTest_attempt', testAttempt)
                thisExp.addData('coinSoundTest_attemptPassed', attemptPassed)
                thisExp.nextEntry()
                if attemptPassed:
                    doneStim = visual.TextStim(
                        win=win, name='coinSoundTestPassedText',
                        text='Great. You identified all 5 coin sounds.',
                        font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                        wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
                    )
                    routineTimer.reset()
                    while routineTimer.getTime() < 1.0:
                        doneStim.draw()
                        if vk_down(0x1B):
                            thisExp.status = FINISHED
                            endExperiment(thisExp, win=win)
                            return
                        win.flip()
                    break

                retryStim = visual.TextStim(
                    win=win, name='coinSoundTestRetryText',
                    text="Some answers were not correct.\n\nWe will listen to the five sounds again.",
                    font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                    wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
                )
                routineTimer.reset()
                while routineTimer.getTime() < 1.5:
                    retryStim.draw()
                    if vk_down(0x1B):
                        thisExp.status = FINISHED
                        endExperiment(thisExp, win=win)
                        return
                    win.flip()

            thisExp.addData('coinSoundTest_completed', True)
            thisExp.addData('coinSoundTest_passingAttempt', testAttempt)
            thisExp.nextEntry()
            routineTimer.reset()





    def response_label_from_key(responseKey):
        return responseKey.upper()

    continueLabel = response_label_from_key(responseKey)



    piggyBankImageFile = os.path.join(baseDir, "piggy-banks", "piggy-bank.png")
    if not os.path.exists(piggyBankImageFile):
        legacyPiggyBankImageFile = os.path.join(baseDir, "piggybank.png")
        if os.path.exists(legacyPiggyBankImageFile):
            piggyBankImageFile = legacyPiggyBankImageFile

    piggyTailImageFile = os.path.join(baseDir, "piggy-banks", "piggy-tail2.png")
    coinImageFiles = {
        0: os.path.join(baseDir, "piggy-banks", "ooc_2p.png"),
        1: os.path.join(baseDir, "piggy-banks", "1p-num.png"),
        2: os.path.join(baseDir, "piggy-banks", "2p-num.png"),
        5: os.path.join(baseDir, "piggy-banks", "5p-num.png"),
        10: os.path.join(baseDir, "piggy-banks", "10p-num.png"),
    }

    PIGGY_BASE_POS = [0, 0.180]
    PIGGY_BODY_SIZE = [0.24, 0.24]
    PIGGY_TAIL_WIDTH = 0.026
    VISUAL_SIGNAL_POS = [0, 0]
    VISUAL_COIN_SIZE = 0.070

    def _image_aspect(imageFile, fallback=1.0):
        try:
            from PIL import Image as PILImage
            if not os.path.exists(imageFile):
                return fallback
            imageSize = PILImage.open(imageFile).size
            aspect = float(imageSize[0]) / float(imageSize[1])
            if np.isfinite(aspect) and aspect > 0:
                return aspect
        except Exception:
            pass
        return fallback

    activePiggyFR = 5
    activePiggyMagnitude = 1
    activeTailCount = 1

    if os.path.exists(piggyBankImageFile):
        piggyStim = visual.ImageStim(
            win=win,
            name='piggyStim',
            image=piggyBankImageFile,
            pos=PIGGY_BASE_POS,
            size=PIGGY_BODY_SIZE,
            units='height'
        )
        piggyTextLabel = None
    else:
        piggyStim = None
        piggyTextLabel = visual.TextStim(
            win=win,
            name='piggyTextLabel',
            text='Piggy bank',
            font='Arial',
            pos=PIGGY_BASE_POS,
            height=0.06,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

    tailAspect = _image_aspect(piggyTailImageFile, fallback=1.0)
    PIGGY_TAIL_HEIGHT = PIGGY_TAIL_WIDTH / tailAspect
    piggyTailStims = []
    if piggyStim is not None and os.path.exists(piggyTailImageFile):
        piggyTailStims.append(
            visual.ImageStim(
                win=win,
                name='piggyTailStim',
                image=piggyTailImageFile,
                pos=PIGGY_BASE_POS,
                size=[PIGGY_TAIL_WIDTH, PIGGY_TAIL_HEIGHT],
                units='height'
            )
        )

    visualSignalCircle1 = visual.ShapeStim(
        win=win, name='visualSignalCircle1',
        size=[0.035, 0.035], vertices='circle',
        ori=0.0, pos=VISUAL_SIGNAL_POS,
        lineWidth=2.0, colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, interpolate=True
    )
    visualSignalCircle2 = visual.ShapeStim(
        win=win, name='visualSignalCircle2',
        size=[0.0175, 0.0175], vertices='circle',
        ori=0.0, pos=VISUAL_SIGNAL_POS,
        lineWidth=2.0, colorSpace='named', lineColor='white', fillColor=None,
        opacity=None, interpolate=True
    )
    visualSignalText = visual.TextStim(
        win=win, name='visualSignalText', text='+', font='Arial Bold',
        pos=VISUAL_SIGNAL_POS, height=0.035,
        color='white', colorSpace='rgb'
    )

    def set_visual_piggy_condition(magnitude=1, frValue=5):

        nonlocal activePiggyFR, activePiggyMagnitude, activeTailCount
        try:
            activePiggyMagnitude = int(magnitude)
        except Exception:
            activePiggyMagnitude = 1
        try:
            activePiggyFR = int(frValue)
        except Exception:
            activePiggyFR = 5
        activeTailCount = 1

        if piggyStim is not None:
            piggyStim.setImage(piggyBankImageFile)
        for tailStim in piggyTailStims:
            tailStim.setImage(piggyTailImageFile)

    def set_piggy_position(pos):

        if pos is None:
            pos = PIGGY_BASE_POS
        pos = [float(pos[0]), float(pos[1])]

        if piggyStim is not None:
            piggyStim.setPos(pos)
        else:
            piggyTextLabel.setPos(pos)

        for tailStim in piggyTailStims:
            tailX = pos[0] + (PIGGY_BODY_SIZE[0] / 2.0) + (PIGGY_TAIL_WIDTH / 2.0) - (PIGGY_TAIL_WIDTH / 20.0)
            tailY = pos[1] + (PIGGY_TAIL_HEIGHT / 2.0)
            tailStim.setPos([tailX, tailY])

    def draw_piggy():
        for tailStim in piggyTailStims[:activeTailCount]:
            tailStim.draw()
        if piggyStim is not None:
            piggyStim.draw()
        else:
            piggyTextLabel.draw()

    def make_falling_coin(value, startTime, x, namePrefix='visualCoin'):

        try:
            value = int(value)
        except Exception:
            value = 0
        imageFile = coinImageFiles.get(value, coinImageFiles.get(0))
        coinStim = None
        if imageFile is not None and os.path.exists(imageFile):
            try:
                coinStim = visual.ImageStim(
                    win=win,
                    name=f'{namePrefix}_{value}_{int(startTime * 1000)}',
                    image=imageFile,
                    pos=[x, 0],
                    size=[VISUAL_COIN_SIZE, VISUAL_COIN_SIZE],
                    units='height'
                )
            except Exception:
                coinStim = None
        return {
            'startTime': startTime,
            'value': value,
            'x': x,
            'stim': coinStim,
        }

    def draw_falling_coin(coin, y, fallbackName='fallingCoin'):

        coinStim = coin.get('stim')
        x = coin.get('x', 0)
        value = coin.get('value', 0)
        if coinStim is not None:
            coinStim.setPos([x, y])
            coinStim.draw()
            return

        coinCircle = visual.ShapeStim(
            win=win,
            name=f'{fallbackName}Circle',
            vertices='circle',
            size=[0.055, 0.055],
            pos=[x, y],
            lineWidth=1.5,
            colorSpace='named',
            lineColor='white',
            fillColor='gold',
            opacity=1.0,
            interpolate=True
        )
        coinText = visual.TextStim(
            win=win,
            name=f'{fallbackName}Text',
            text=f'{value}p',
            font='Arial',
            pos=[x, y],
            height=0.022,
            color='black',
            colorSpace='rgb'
        )
        coinCircle.draw()
        coinText.draw()

    def draw_piggy_with_signal(symbol='+', pos=None):
        if pos is None:
            pos = PIGGY_BASE_POS
        set_piggy_position(pos)
        draw_piggy()
        visualSignalCircle1.setPos(VISUAL_SIGNAL_POS)
        visualSignalCircle2.setPos(VISUAL_SIGNAL_POS)
        visualSignalText.setPos(VISUAL_SIGNAL_POS)
        visualSignalText.setText(symbol)
        visualSignalCircle1.draw()
        visualSignalCircle2.draw()
        visualSignalText.draw()




    def fixation_only_space_screen():

        spaceWasDown = vk_down(0x20)
        routineTimer.reset()
        while True:
            circle_fix1.draw()
            circle_fix2.draw()
            fix_.draw()

            spaceDown = vk_down(0x20)
            if spaceDown and not spaceWasDown:
                routineTimer.reset()
                return True

            spaceWasDown = spaceDown

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()


    def instruction_screen(mainText, showPiggy=False, piggySignal=None, textPos=[0, 0.04], requiredPresses=1):

        mainTextHeight = fitted_text_height(mainText, preferred=TASK_TEXT_HEIGHT, minimum=TASK_TEXT_MIN_HEIGHT, available_height=0.36)
        mainStim = visual.TextStim(
            win=win, name='instructionMainText', text=mainText, font='Arial',
            pos=textPos, height=mainTextHeight, wrapWidth=CENTRAL_TEXT_WRAP,
            color='white', colorSpace='rgb'
        )
        bottomStim = visual.TextStim(
            win=win, name='instructionBottomText', text='', font='Arial',
            pos=[0, BOTTOM_PROMPT_Y], height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP, color='white', colorSpace='rgb'
        )
        spaceWasDown = vk_down(0x20)
        pressCounter = 0
        routineTimer.reset()

        while True:
            holdOK = hold_keys_ok(holdVKCodes)
            spaceDown = vk_down(0x20)
            if showPiggy:
                if piggySignal is None:
                    draw_piggy()
                else:
                    draw_piggy_with_signal(piggySignal)
            mainStim.draw()
            if holdOK:
                if requiredPresses == 1:
                    bottomStim.setText("Press SPACE to continue.")
                elif pressCounter == 0:
                    bottomStim.setText("Press SPACE twice to continue.")
                else:
                    bottomStim.setText("Press SPACE one more time to continue.")
            else:
                bottomStim.setText("Keep holding the three marked keys.")
            bottomStim.draw()
            if spaceDown and not spaceWasDown and holdOK:
                pressCounter += 1
                if pressCounter >= requiredPresses:
                    break
            spaceWasDown = spaceDown
            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False
            win.flip()

        routineTimer.reset()
        return True


    def understanding_screen(questionText):




        understandingMainText = (
            f"{questionText}\n\n"
            f"Press {continueLabel} to continue.\n\n"
            "Press SPACE to see this part again."
        )
        understandStim = visual.TextStim(
            win=win,
            name='understandingText',
            text=understandingMainText,
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=fitted_text_height(understandingMainText, preferred=TASK_TEXT_HEIGHT, minimum=TASK_TEXT_MIN_HEIGHT, available_height=0.34),
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        bottomStim = visual.TextStim(
            win=win,
            name='understandingBottomText',
            text='',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        responseWasDown = vk_down(responseVKCode)
        spaceWasDown = vk_down(0x20)
        routineTimer.reset()

        choice = None

        while True:
            holdOK = hold_keys_ok(holdVKCodes)
            responseDown = vk_down(responseVKCode)
            spaceDown = vk_down(0x20)

            understandStim.draw()

            if holdOK:
                bottomStim.setText("Choose when you are ready.")
            else:
                bottomStim.setText("Keep holding the three marked keys.")

            bottomStim.draw()

            if responseDown and not responseWasDown and holdOK:
                choice = "continue"
                break

            if spaceDown and not spaceWasDown and holdOK:
                choice = "repeat"
                break

            responseWasDown = responseDown
            spaceWasDown = spaceDown

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return None

            win.flip()

        routineTimer.reset()
        return choice


    def true_false_quiz_screen(quizName, questions):









        trueLabel = continueLabel
        falseLabel = 'SPACE'

        titleStim = visual.TextStim(
            win=win,
            name=f'{quizName}_title',
            text='Quick check',
            font='Arial',
            pos=[0, 0.200],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        questionStim = visual.TextStim(
            win=win,
            name=f'{quizName}_question',
            text='',
            font='Arial',
            pos=[0, 0.070],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        choiceStim = visual.TextStim(
            win=win,
            name=f'{quizName}_choices',
            text='',
            font='Arial',
            pos=[0, -0.105],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        bottomStim = visual.TextStim(
            win=win,
            name=f'{quizName}_bottom',
            text='',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        feedbackStim = visual.TextStim(
            win=win,
            name=f'{quizName}_feedback',
            text='',
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        quizAttempt = 1
        try:
            quizAttempt = int(thisExp.extraInfo.get(f'{quizName}_attempt', 0)) + 1
            thisExp.extraInfo[f'{quizName}_attempt'] = quizAttempt
        except Exception:
            pass

        nCorrect = 0

        for qNum, questionText in enumerate(questions, start=1):
            responseWasDown = vk_down(responseVKCode)
            spaceWasDown = vk_down(0x20)
            responseClock = core.Clock()
            choice = None
            rt = None

            quizQuestionDisplay = f'{qNum}/3\n\n{questionText}'
            questionStim.setText(quizQuestionDisplay)
            questionStim.setHeight(fitted_text_height(quizQuestionDisplay, preferred=TASK_TEXT_HEIGHT, minimum=TASK_TEXT_MIN_HEIGHT, available_height=0.18))
            choiceStim.setText(
                f'TRUE = press {trueLabel}\n'
                f'FALSE = press {falseLabel}'
            )

            while choice is None:
                holdOK = hold_keys_ok(holdVKCodes)
                responseDown = vk_down(responseVKCode)
                spaceDown = vk_down(0x20)

                titleStim.draw()
                questionStim.draw()
                choiceStim.draw()

                if holdOK:
                    bottomStim.setText('Choose TRUE or FALSE.')
                else:
                    bottomStim.setText('Keep holding the three marked keys.')
                bottomStim.draw()

                if responseDown and not responseWasDown and holdOK:
                    choice = 'true'
                    rt = responseClock.getTime()

                elif spaceDown and not spaceWasDown and holdOK:
                    choice = 'false'
                    rt = responseClock.getTime()

                responseWasDown = responseDown
                spaceWasDown = spaceDown

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            correct = (choice == 'true')
            if correct:
                nCorrect += 1

            thisExp.addData(f'{quizName}_attempt', quizAttempt)
            thisExp.addData(f'{quizName}_questionNumber', qNum)
            thisExp.addData(f'{quizName}_questionText', questionText)
            thisExp.addData(f'{quizName}_choice', choice)
            thisExp.addData(f'{quizName}_correctAnswer', 'true')
            thisExp.addData(f'{quizName}_correct', correct)
            thisExp.addData(f'{quizName}_rt', rt)
            thisExp.nextEntry()

            feedbackStim.setText('Correct.' if correct else 'Not quite.')
            routineTimer.reset()
            while routineTimer.getTime() < 0.65:
                feedbackStim.draw()
                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None
                win.flip()

        passed = (nCorrect == len(questions))
        thisExp.addData(f'{quizName}_attempt', quizAttempt)
        thisExp.addData(f'{quizName}_nCorrect', nCorrect)
        thisExp.addData(f'{quizName}_nQuestions', len(questions))
        thisExp.addData(f'{quizName}_passed', passed)
        thisExp.nextEntry()

        if passed:
            feedbackText = 'Great. You are ready to practise.'
        else:
            feedbackText = (
                'Some answers were not correct.\n\n'
                'We will go through the instructions again.'
            )

        feedbackStim.setText(feedbackText)
        routineTimer.reset()
        while routineTimer.getTime() < 1.5:
            feedbackStim.draw()
            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return None
            win.flip()

        routineTimer.reset()
        return passed



    def coin_value_from_fbfile(fbFileName):

        f = str(fbFileName).lower()
        if "5p" in f:
            return 5
        if "1p" in f:
            return 1
        return 0


    def play_visual_piggy_cue(
        cueFileForDemo,
        bottomText="Listen. Do not press yet.",
        keepPlayingUntilStopped=False,
        stopOnEarlyPress=False,
        logPrefix="visualCue",
        visualMagnitude=1,
        visualFR=5,
        waitForSpace=False
    ):

        set_visual_piggy_condition(visualMagnitude, visualFR)

        listenText = visual.TextStim(
            win=win,
            name='visualPiggyCueText',
            text=bottomText,
            font='Arial',
            pos=[0, -0.160],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        continueText = visual.TextStim(
            win=win,
            name='visualPiggyCueContinueText',
            text='Press SPACE to continue.',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        holdWarningText = visual.TextStim(
            win=win,
            name='visualPiggyCueHoldWarningText',
            text='Keep pressing the three marked keys at the same time.',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        holdWarningUntil = -1.0

        cueSound = make_lab_sound(
            cueFileForDemo,
            secs=(-1 if keepPlayingUntilStopped else 1.4),
            stereo=True,
            hamming=True,
            name='visualPiggyCueSound'
        )
        cueSound.setVolume(1.0)

        played = False
        clear_response_key_events()
        spaceWasDown = vk_down(0x20)
        routineTimer.reset()
        tracker_event(
            "visual_cue_phase_start",
            cueFile=cueFileForDemo,
            keepPlaying=keepPlayingUntilStopped,
            waitForSpace=waitForSpace
        )

        while True:
            nowTime = routineTimer.getTime()
            draw_piggy_with_signal('×')
            listenText.draw()

            if not played:
                win.callOnFlip(routineTimer.reset)
                schedule_sound_on_next_flip(
                    cueSound,
                    'visual_cue',
                    cueFile=cueFileForDemo,
                    keepPlaying=keepPlayingUntilStopped,
                )
                played = True

            holdOK = hold_keys_ok(holdVKCodes)
            spaceDown = vk_down(0x20)
            early_events = get_response_keypresses() if nowTime < 1.4 else []
            if stopOnEarlyPress and early_events:
                early_time = press_global_time(early_events[0])
                if holdOK:
                    tracker_event("visual_early_press_before_plus", round=logPrefix, cueFile=cueFileForDemo, globalTime=f"{early_time:.6f}")
                    cueSound.stop()
                    thisExp.addData(f'{logPrefix}_earlyPressBeforePlus', True)
                    thisExp.addData(f'{logPrefix}_earlyPressTime', early_time)
                    thisExp.nextEntry()
                    routineTimer.reset()
                    return 'EARLY_PRESS'
                else:
                    holdWarningUntil = nowTime + 0.8
                    tracker_event("visual_invalid_press_without_hold_during_cue", round=logPrefix, cueFile=cueFileForDemo, globalTime=f"{early_time:.6f}")
                    thisExp.addData(f'{logPrefix}_invalidPressWithoutHoldDuringCue', True)
                    thisExp.addData(f'{logPrefix}_invalidPressWithoutHoldDuringCueTime', early_time)
                    thisExp.nextEntry()

            if waitForSpace:
                continueText.draw()
            elif (not holdOK) or (nowTime < holdWarningUntil):
                holdWarningText.draw()

            if waitForSpace and nowTime >= 1.4 and spaceDown and not spaceWasDown:
                if keepPlayingUntilStopped:
                    routineTimer.reset()
                    return cueSound
                cueSound.stop()
                routineTimer.reset()
                return True
            spaceWasDown = spaceDown

            if not waitForSpace and nowTime >= 1.4:
                if keepPlayingUntilStopped:
                    routineTimer.reset()
                    return cueSound
                cueSound.stop()
                routineTimer.reset()
                return True

            if vk_down(0x1B):
                cueSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()


    def run_visual_instruction_demo_round(cueFileForDemo):









        demoFR = 5
        demoCoinValue = 1
        demoRewardFile = resolve_reward_file('1pclickres.wav')

        cueSound = make_lab_sound(
            cueFileForDemo,
            secs=-1,
            stereo=True,
            hamming=True,
            name='visualInstructionDemoCueSound'
        )
        cueSound.setVolume(1.0)

        rewardSound = make_lab_sound(
            demoRewardFile,
            secs=-1,
            stereo=True,
            hamming=True,
            name='visualInstructionDemoRewardSound'
        )
        rewardSound.setVolume(1.0)

        demoText = visual.TextStim(
            win=win,
            name='visualInstructionDemoText',
            text='',
            font='Arial',
            pos=[0, -0.160],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        demoContinueText = visual.TextStim(
            win=win,
            name='visualInstructionDemoContinueText',
            text='Press SPACE to continue.',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        holdWarningText = visual.TextStim(
            win=win,
            name='visualInstructionDemoHoldWarningText',
            text='Keep holding the three marked keys at the same time.',
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        demoWaitText = (
            "In the main task, you will hear a sound and see ×.\n\n"
            "Wait and do not press yet.\n\n"
            "The piggy bank will not appear then."
        )
        demoPressText = (
            f"When the symbol changes to +, press {continueLabel} "
            "to shake the piggy bank.\n\n"
            "Keep holding F, T and H."
        )
        demoRewardText = (
            "You got a coin.\n\n"
            "Keep pressing to get more coins.\n\n"
            "Press SPACE to continue."
        )

        set_visual_piggy_condition(demoCoinValue, demoFR)
        cueTiming = None
        clear_response_key_events()
        spaceWasDown = vk_down(0x20)
        waitWarningUntil = -1.0
        routineTimer.reset()

        while True:
            nowTime = routineTimer.getTime()
            draw_piggy_with_signal('×', PIGGY_BASE_POS)
            demoText.setText(demoWaitText)
            demoText.draw()
            demoContinueText.draw()

            if cueTiming is None:
                win.callOnFlip(routineTimer.reset)
                cueTiming = schedule_sound_on_next_flip(
                    cueSound,
                    'visual_instruction_demo_cue',
                    cueFile=cueFileForDemo,
                    phase='wait',
                )
            spaceDown = vk_down(0x20)
            for keyEvent in get_response_keypresses():
                waitWarningUntil = nowTime + 0.8
                tracker_event(
                    "visual_instruction_demo_press_during_wait",
                    globalTime=f"{press_global_time(keyEvent):.6f}"
                )

            if nowTime < waitWarningUntil:
                holdWarningText.setText("Wait for + before pressing.")
                holdWarningText.draw()

            if nowTime >= 1.4 and spaceDown and not spaceWasDown:
                break
            spaceWasDown = spaceDown

            if vk_down(0x1B):
                cueSound.stop()
                rewardSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        pressCount = 0
        invalidPressCount = 0
        rewardCount = 0
        earnedPence = 0
        nextThresh = demoFR
        firstCoinEarned = False
        clear_response_key_events()
        spaceWasDown = vk_down(0x20)
        shakeUntil = -1.0
        shakeDur = 0.12
        shakeAmp = 0.018
        invalidWarningUntil = -1.0
        fallingCoins = []
        coinFallDur = 0.65
        coinStartY = 0.115
        coinEndY = 0.015

        def draw_demo_falling_coins(nowTime):
            activeCoins = []
            for coin in fallingCoins:
                age = nowTime - coin['startTime']
                if age <= coinFallDur:
                    progress = age / coinFallDur
                    y = coinStartY + (coinEndY - coinStartY) * progress
                    x = coin['x']

                    draw_falling_coin(coin, y, fallbackName='visualInstructionDemoCoin')
                    activeCoins.append(coin)
            fallingCoins[:] = activeCoins

        routineTimer.reset()
        tracker_event(
            "visual_instruction_demo_press_window_start",
            cueFile=cueFileForDemo,
            FR=demoFR
        )

        while True:
            nowTime = routineTimer.getTime()
            holdOK = hold_keys_ok(holdVKCodes)
            spaceDown = vk_down(0x20)

            for keyEvent in get_response_keypresses():
                eventGlobalTime = press_global_time(keyEvent)
                if holdOK:
                    pressCount += 1
                    shakeUntil = nowTime + shakeDur

                    while pressCount >= nextThresh:
                        rewardSound.stop()
                        schedule_sound_on_next_flip(
                            rewardSound,
                            'visual_instruction_demo_reward_sound',
                            visual_marker=False,
                            rewardNumber=rewardCount + 1,
                            threshold=nextThresh,
                            pressGlobalTime=f"{eventGlobalTime:.6f}",
                        )
                        rewardCount += 1
                        earnedPence += demoCoinValue
                        fallingCoins.append(
                            make_falling_coin(
                                demoCoinValue,
                                nowTime,
                                py_random.choice([-1, 1]) * py_random.uniform(0.20, 0.25),
                                namePrefix='visualInstructionDemoCoin'
                            )
                        )
                        nextThresh += demoFR
                        firstCoinEarned = True
                else:
                    invalidPressCount += 1
                    invalidWarningUntil = nowTime + 0.8
                    tracker_event(
                        "visual_instruction_demo_invalid_press_without_hold",
                        invalidPressNumber=invalidPressCount,
                        localTime=f"{nowTime:.6f}",
                        globalTime=f"{eventGlobalTime:.6f}",
                    )

            if nowTime < shakeUntil:
                xOffset = shakeAmp * math.sin(nowTime * 90.0)
            else:
                xOffset = 0.0
            currentPiggyPos = [PIGGY_BASE_POS[0] + xOffset, PIGGY_BASE_POS[1]]
            draw_piggy_with_signal('+', currentPiggyPos)
            draw_demo_falling_coins(nowTime)

            if firstCoinEarned:
                demoText.setText(demoRewardText)
            else:
                demoText.setText(demoPressText)
            demoText.draw()

            if not holdOK:
                holdWarningText.setText("Keep holding the three marked keys at the same time.")
                holdWarningText.draw()
            elif nowTime < invalidWarningUntil:
                holdWarningText.setText("Keep holding F, T and H before you press.")
                holdWarningText.draw()

            if firstCoinEarned and spaceDown and not spaceWasDown and holdOK:
                break
            spaceWasDown = spaceDown

            if vk_down(0x1B):
                cueSound.stop()
                rewardSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        cueSound.stop()
        rewardSound.stop()
        set_piggy_position(PIGGY_BASE_POS)

        thisExp.addData('visualInstructionDemo_cueFile', cueFileForDemo)
        thisExp.addData('visualInstructionDemo_rewardFile', demoRewardFile)
        thisExp.addData('visualInstructionDemo_FR', demoFR)
        thisExp.addData('visualInstructionDemo_pressCount', pressCount)
        thisExp.addData('visualInstructionDemo_invalidPressCount', invalidPressCount)
        thisExp.addData('visualInstructionDemo_rewardCount', rewardCount)
        thisExp.addData('visualInstructionDemo_earnedPence', earnedPence)
        thisExp.addData('visualInstructionDemo_completed', True)
        thisExp.nextEntry()

        tracker_event(
            "visual_instruction_demo_completed",
            pressCount=pressCount,
            rewardCount=rewardCount
        )
        routineTimer.reset()
        return True


    def get_practice_trial(allConditions, targetMagnitude, targetFR):

        for row in allConditions:
            try:
                if int(row['mag']) == int(targetMagnitude) and int(row['FR']) == int(targetFR):
                    return row
            except Exception:
                continue

        raise RuntimeError(
            f"Missing visual-practice condition: {int(targetMagnitude)}p, FR{int(targetFR)}."
        )




    def visual_clicking_window(fbFileForDemo, FRForDemo, logPrefix="visualPractice", cueSoundToStop=None):












        startText = visual.TextStim(
            win=win,
            name='visualStartText',
            text="",
            font='Arial',
            pos=[0, CENTRAL_TEXT_TOP_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        reminderText = visual.TextStim(
            win=win,
            name='visualReminderText',
            text="",
            font='Arial',
            pos=[0, CENTRAL_TEXT_LOW_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        holdWarningText = visual.TextStim(
            win=win,
            name='visualHoldWarningText',
            text="Keep pressing the three marked keys at the same time.",
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        rewardSoundFile = fbFileForDemo

        clickDur = py_random.uniform(4.0, 6.0)

        FRForDemo = int(FRForDemo)
        coinValue = coin_value_from_fbfile(fbFileForDemo)
        set_visual_piggy_condition(coinValue, FRForDemo)

        pressCount = 0
        invalidPressCount = 0
        invalidPressRTs = []
        invalidPressGlobalTimes = []
        invalidPressKeys = []
        rewardCount = 0
        rewardTriggerPressRTs = []
        rewardTriggerPressGlobalTimes = []
        rewardAudioPlannedOnsetGlobals = []
        rewardAudioPlannedOnsetsPTB = []
        rewardThresholds = []
        rewardNumbers = []
        earnedPence = 0
        rewardSoundObjects = []

        def stop_reward_sounds():
            for rewardSound in rewardSoundObjects:
                try:
                    rewardSound.stop()
                except Exception:
                    pass

        nextThresh = FRForDemo
        clear_response_key_events()

        basePiggyPos = list(PIGGY_BASE_POS)
        shakeUntil = -1
        shakeDur = 0.12
        shakeAmp = 0.018

        fallingCoins = []
        coinFallDur = 0.65
        coinStartY = 0.115
        coinEndY = 0.015

        def coin_colour(value):
            if value == 1:
                return 'gold'
            elif value == 2:
                return 'orange'
            elif value == 5:
                return 'deepskyblue'
            else:
                return 'white'

        def draw_animated_piggy(nowTime):
            if nowTime < shakeUntil:
                shakePhase = math.sin(nowTime * 90)
                xOffset = shakeAmp * shakePhase
            else:
                xOffset = 0

            currentPos = [basePiggyPos[0] + xOffset, basePiggyPos[1]]

            draw_piggy_with_signal('+', currentPos)

        def draw_falling_coins(nowTime):
            activeCoins = []

            for coin in fallingCoins:
                age = nowTime - coin["startTime"]

                if age <= coinFallDur:
                    progress = age / coinFallDur
                    y = coinStartY + (coinEndY - coinStartY) * progress
                    x = coin["x"]

                    draw_falling_coin(coin, y, fallbackName='fallingCoin')

                    activeCoins.append(coin)

            fallingCoins[:] = activeCoins

        routineTimer.reset()
        start_phase_on_next_flip(
            "visual_click_phase_start",
            trial=logPrefix,
            clickDur=f"{clickDur:.6f}",
            FR=FRForDemo,
            fbFile=fbFileForDemo,
        )
        plusTiming = mark_visual_on_next_flip(
            "visual_plus_visual_onset", trial=logPrefix
        )

        while routineTimer.getTime() < clickDur:
            t = routineTimer.getTime()

            for keyEvent in get_response_keypresses():
                responseGlobalT = press_global_time(keyEvent)
                plus_reference = plusTiming['visual_onset_global'] or responseGlobalT
                responseLocalT = responseGlobalT - plus_reference
                holdOK = hold_keys_ok(holdVKCodes)
                if holdOK:
                    pressCount += 1

                    shakeUntil = responseLocalT + shakeDur

                    while pressCount >= nextThresh:
                        rewardLocalT = responseLocalT
                        rewardGlobalT = responseGlobalT
                        rewardThreshold = nextThresh

                        rewardNumber = rewardCount + 1
                        rewardSound = make_lab_sound(
                            rewardSoundFile,
                            secs=-1,
                            stereo=True,
                            hamming=True,
                            name=f'visualRewardSound_{logPrefix}_{rewardNumber}',
                        )
                        rewardSound.setVolume(REWARD_SOUND_VOLUME)
                        rewardSoundObjects.append(rewardSound)
                        rewardTiming = schedule_sound_on_next_flip(
                            rewardSound,
                            'visual_reward_sound',
                            visual_marker=False,
                            trial=logPrefix,
                            rewardNumber=rewardNumber,
                            threshold=rewardThreshold,
                            pressGlobalTime=f"{rewardGlobalT:.6f}",
                            overlapEnabled=int(REWARD_SOUND_OVERLAP_ENABLED),
                        )

                        rewardCount += 1
                        rewardTriggerPressRTs.append(rewardLocalT)
                        rewardTriggerPressGlobalTimes.append(rewardGlobalT)
                        rewardAudioPlannedOnsetGlobals.append(rewardTiming['audio_planned_onset_global'])
                        rewardAudioPlannedOnsetsPTB.append(rewardTiming['audio_planned_onset_ptb'])
                        rewardThresholds.append(rewardThreshold)
                        rewardNumbers.append(rewardCount)
                        earnedPence += coinValue

                        fallingCoins.append(
                            make_falling_coin(
                                coinValue,
                                t,
                                py_random.choice([-1, 1]) * py_random.uniform(0.20, 0.25),
                                namePrefix='fallingCoin'
                            )
                        )

                        nextThresh += FRForDemo
                else:
                    invalidPressCount += 1
                    invalidPressRTs.append(responseLocalT)
                    invalidPressGlobalTimes.append(responseGlobalT)
                    invalidPressKeys.append(responseKey)
                    tracker_event(
                        "visual_invalid_press",
                        trial=logPrefix,
                        invalidPressNumber=invalidPressCount,
                        localTime=f"{responseLocalT:.6f}",
                        globalTime=f"{responseGlobalT:.6f}",
                    )

            draw_animated_piggy(t)
            draw_falling_coins(t)

            if not hold_keys_ok(holdVKCodes):
                holdWarningText.draw()

            if vk_down(0x1B):
                stop_reward_sounds()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return None

            win.flip()

        tracker_event("visual_click_phase_end", trial=logPrefix)
        if cueSoundToStop is not None:
            try:
                cueSoundToStop.stop()
            except Exception:
                pass

        set_piggy_position(basePiggyPos)

        thisExp.addData(f'{logPrefix}_plusVisualOnsetGlobal', plusTiming['visual_onset_global'])
        thisExp.addData(f'{logPrefix}_clickDur', clickDur)
        thisExp.addData(f'{logPrefix}_FR', FRForDemo)
        thisExp.addData(f'{logPrefix}_fbFile', fbFileForDemo)
        thisExp.addData(f'{logPrefix}_coinValue', coinValue)
        thisExp.addData(f'{logPrefix}_pressCount', pressCount)
        thisExp.addData(f'{logPrefix}_invalidPressCount', invalidPressCount)
        thisExp.addData(f'{logPrefix}_invalidPressRTs', invalidPressRTs)
        thisExp.addData(f'{logPrefix}_invalidPressGlobalTimes', invalidPressGlobalTimes)
        thisExp.addData(f'{logPrefix}_invalidPressKeys', invalidPressKeys)
        thisExp.addData(f'{logPrefix}_rewardCount', rewardCount)
        thisExp.addData(f'{logPrefix}_rewardTriggerPressRTs', rewardTriggerPressRTs)
        thisExp.addData(f'{logPrefix}_rewardTriggerPressGlobalTimes', rewardTriggerPressGlobalTimes)
        thisExp.addData(f'{logPrefix}_rewardAudioPlannedOnsetGlobals', rewardAudioPlannedOnsetGlobals)
        thisExp.addData(f'{logPrefix}_rewardAudioPlannedOnsetsPTB', rewardAudioPlannedOnsetsPTB)
        thisExp.addData(f'{logPrefix}_rewardThresholds', rewardThresholds)
        thisExp.addData(f'{logPrefix}_rewardNumbers', rewardNumbers)
        thisExp.addData(f'{logPrefix}_earnedPence', earnedPence)
        thisExp.nextEntry()

        routineTimer.reset()

        return {
            "clickDur": clickDur,
            "plusTiming": plusTiming,
            "FR": FRForDemo,
            "fbFile": fbFileForDemo,
            "coinValue": coinValue,
            "pressCount": pressCount,
            "invalidPressCount": invalidPressCount,
            "invalidPressRTs": invalidPressRTs,
            "invalidPressGlobalTimes": invalidPressGlobalTimes,
            "rewardCount": rewardCount,
            "rewardTriggerPressRTs": rewardTriggerPressRTs,
            "rewardTriggerPressGlobalTimes": rewardTriggerPressGlobalTimes,
            "rewardAudioPlannedOnsetGlobals": rewardAudioPlannedOnsetGlobals,
            "rewardAudioPlannedOnsetsPTB": rewardAudioPlannedOnsetsPTB,
            "rewardSoundObjects": rewardSoundObjects,
            "earnedPence": earnedPence
        }


    def result_screen(earnedPence, example=False, requiredPresses=1):
        if example:
            txt = (
                f"You earned {earnedPence}p in this example.\n\n"
                ""
            )
        else:
            txt = (
                f"You earned {earnedPence}p in this round.\n\n"
                ""
            )

        return instruction_screen(
            txt,
            showPiggy=False,
            textPos=[0, 0.04],
            requiredPresses=requiredPresses
        )


    def show_visual_early_press_warning():
        nonlocal visualPracticePenaltyPence
        visualPracticePenaltyPence += 1
        thisExp.addData('visualPractice_earlyPressPenaltyPence', 1)
        thisExp.addData('visualPractice_totalPenaltyPence', visualPracticePenaltyPence)
        thisExp.nextEntry()
        warningStim = visual.TextStim(
            win=win,
            name='visualEarlyPressWarningText',
            text=(
                "Please wait until the symbol changes to + before pressing.\n\n"
                "Each press during × loses 1 pence.\n\n"
                "Press SPACE to start this practice round again."
            ),
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        spaceWasDown = vk_down(0x20)
        while True:
            warningStim.draw()
            spaceDown = vk_down(0x20)
            if spaceDown and not spaceWasDown:
                routineTimer.reset()
                return True
            spaceWasDown = spaceDown
            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False
            win.flip()


    def run_visual_practice_trial(trialRow, trialNumber):







        attemptNum = 0

        while True:
            attemptNum += 1
            logPrefix = f'visualPractice_round{trialNumber}_attempt{attemptNum}'

            cueFileForPractice, cueVersionForPractice = next_visual_practice_cue_file()
            thisExp.addData(f'{logPrefix}_cueFile', cueFileForPractice)
            thisExp.addData(f'{logPrefix}_cueVersion', cueVersionForPractice)
            thisExp.nextEntry()

            cueResult = play_visual_piggy_cue(
                cueFileForPractice,
                bottomText="Listen. Do not press yet.",
                keepPlayingUntilStopped=True,
                stopOnEarlyPress=True,
                logPrefix=logPrefix,
                visualMagnitude=trialRow['mag'],
                visualFR=trialRow['FR']
            )
            if cueResult == 'EARLY_PRESS':
                ok = show_visual_early_press_warning()
                if not ok:
                    return None
                continue
            if not cueResult:
                return None

            result = visual_clicking_window(
                fbFileForDemo=trialRow['fbFile'],
                FRForDemo=trialRow['FR'],
                logPrefix=logPrefix,
                cueSoundToStop=cueResult
            )

            if result is None:
                return None

            ok = result_screen(
                result["earnedPence"],
                example=False,
                requiredPresses=2
            )
            if not ok:
                return None

            return result




    def run_fixation_demo():
        demoFixText = visual.TextStim(
            win=win,
            name='demoFixText',
            text='+',
            font='Arial Bold',
            pos=[0, 0],
            height=0.035,
            color='white',
            colorSpace='rgb'
        )

        demoFixCircle1 = visual.ShapeStim(
            win=win,
            name='demoFixCircle1',
            size=[0.035, 0.035],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoFixCircle2 = visual.ShapeStim(
            win=win,
            name='demoFixCircle2',
            size=[0.0175, 0.0175],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoFixDur = 1.5
        routineTimer.reset()

        while routineTimer.getTime() < demoFixDur:
            demoFixCircle1.draw()
            demoFixCircle2.draw()
            demoFixText.draw()

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        routineTimer.reset()
        return True


    def run_centre_cue_demo(cueFileForDemo):
        demoCueText = visual.TextStim(
            win=win,
            name='demoCueText',
            text='+',
            font='Arial Bold',
            pos=[0, 0],
            height=0.035,
            color='white',
            colorSpace='rgb'
        )

        demoCueCircle1 = visual.ShapeStim(
            win=win,
            name='demoCueCircle1',
            size=[0.035, 0.035],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoCueCircle2 = visual.ShapeStim(
            win=win,
            name='demoCueCircle2',
            size=[0.0175, 0.0175],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoCueSound = make_lab_sound(
            cueFileForDemo,
            secs=1.4,
            stereo=True,
            hamming=True,
        name='demoCueSound'
        )
        demoCueSound.setVolume(1.0)

        played = False
        routineTimer.reset()

        while routineTimer.getTime() < 1.4:
            if not played:
                demoCueSound.play()
                played = True

            demoCueCircle1.draw()
            demoCueCircle2.draw()
            demoCueText.draw()

            if vk_down(0x1B):
                demoCueSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        demoCueSound.stop()
        routineTimer.reset()
        return True


    def run_centre_clicking_demo(fbFileForDemo, FRForDemo):
        demoClickText = visual.TextStim(
            win=win,
            name='demoClickText',
            text='+',
            font='Arial Bold',
            pos=[0, 0],
            height=0.035,
            color='white',
            colorSpace='rgb'
        )

        demoClickCircle1 = visual.ShapeStim(
            win=win,
            name='demoClickCircle1',
            size=[0.035, 0.035],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoClickCircle2 = visual.ShapeStim(
            win=win,
            name='demoClickCircle2',
            size=[0.0175, 0.0175],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoRewardSound = make_lab_sound(
            fbFileForDemo,
            secs=-1,
            stereo=True,
            hamming=True,
        name='demoRewardSound'
        )
        demoRewardSound.setVolume(1.0)

        demoClickDur = py_random.uniform(4.0, 6.0)

        pressCount = 0
        invalidPressCount = 0
        nextThresh = int(FRForDemo)
        lastCount = 0
        clear_response_key_events()

        routineTimer.reset()

        while routineTimer.getTime() < demoClickDur:
            holdOK = hold_keys_ok(holdVKCodes)

            for _ in get_response_keypresses():
                if holdOK:
                    pressCount += 1
                else:
                    invalidPressCount += 1

            if pressCount > lastCount:
                while pressCount >= nextThresh:
                    demoRewardSound.stop()
                    schedule_sound_on_next_flip(
                        demoRewardSound,
                        'centre_demo_reward_sound',
                        visual_marker=False,
                        threshold=nextThresh,
                    )
                    nextThresh += int(FRForDemo)

            lastCount = pressCount

            demoClickCircle1.draw()
            demoClickCircle2.draw()
            demoClickText.draw()

            if vk_down(0x1B):
                demoRewardSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        demoRewardSound.stop()

        nRewards = math.floor(pressCount / int(FRForDemo))
        coinValue = coin_value_from_fbfile(fbFileForDemo)
        earnedPence = nRewards * coinValue

        thisExp.addData('centreDemo_pressCount', pressCount)
        thisExp.addData('centreDemo_invalidPressCount', invalidPressCount)
        thisExp.addData('centreDemo_clickDur', demoClickDur)
        thisExp.addData('centreDemo_FR', int(FRForDemo))
        thisExp.addData('centreDemo_coinValue', coinValue)
        thisExp.addData('centreDemo_nRewards', nRewards)
        thisExp.addData('centreDemo_earnedPence', earnedPence)
        thisExp.nextEntry()

        routineTimer.reset()

        return {
            "pressCount": pressCount,
            "nRewards": nRewards,
            "earnedPence": earnedPence
        }


    def run_end_symbol_demo(duration=1.5):
        demoITIText = visual.TextStim(
            win=win,
            name='demoITIText',
            text='×',
            font='Arial Bold',
            pos=[0, 0],
            height=0.035,
            color='white',
            colorSpace='rgb'
        )

        demoITICircle1 = visual.ShapeStim(
            win=win,
            name='demoITICircle1',
            size=[0.035, 0.035],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        demoITICircle2 = visual.ShapeStim(
            win=win,
            name='demoITICircle2',
            size=[0.0175, 0.0175],
            vertices='circle',
            ori=0.0,
            pos=[0, 0],
            lineWidth=1.0,
            colorSpace='named',
            lineColor='white',
            fillColor=None,
            opacity=None,
            interpolate=True
        )

        routineTimer.reset()

        while routineTimer.getTime() < duration:
            demoITICircle1.draw()
            demoITICircle2.draw()
            demoITIText.draw()

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()

        routineTimer.reset()
        return True


    if RUN_VISUAL_PRACTICE:




        practiceConditionsForInstruction = participantMappedMainRows
        visualExampleTrial = practiceConditionsForInstruction[0]

        repeatVisualInstruction = True

        while repeatVisualInstruction:

            ok = instruction_screen(
                "Now we will practise the task.",
                showPiggy=False,
                textPos=[0, 0.04]
            )
            if not ok:
                return

            exampleCueFile, exampleCueVersion = next_visual_practice_cue_file()
            thisExp.addData('visualExampleCueFile', exampleCueFile)
            thisExp.addData('visualExampleCueVersion', exampleCueVersion)
            thisExp.nextEntry()

            ok = run_visual_instruction_demo_round(exampleCueFile)
            if not ok:
                return

            visualChoice = understanding_screen("Do you understand what to do?")

            if visualChoice is None:
                return

            if visualChoice == "continue":
                repeatVisualInstruction = False
            else:
                repeatVisualInstruction = True






        ok = instruction_screen(
            "Remember, piggy banks are not all the same. "
            "Some pay out higher value coins. Others need more presses before a coin drops.",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return

        visualPracticeRows = [
            get_practice_trial(practiceConditionsForInstruction, 5, 1),
            get_practice_trial(practiceConditionsForInstruction, 1, 5),
            get_practice_trial(practiceConditionsForInstruction, 1, 10),
        ]

        visualPracticeTotalEarned = 0
        visualPracticeTotalAfterPenalty = 0

        for visualTrialNumber, visualTrialRow in enumerate(visualPracticeRows, start=1):
            visualTrialResult = run_visual_practice_trial(visualTrialRow, visualTrialNumber)

            if visualTrialResult is None:
                return

            visualPracticeTotalEarned += visualTrialResult["earnedPence"]


        visualPracticeTotalAfterPenalty = visualPracticeTotalEarned - visualPracticePenaltyPence
        thisExp.addData('visualPractice_totalEarnedBeforePenalty', visualPracticeTotalEarned)
        thisExp.addData('visualPractice_totalPenaltyPence', visualPracticePenaltyPence)
        thisExp.addData('visualPractice_totalEarnedAfterPenalty', visualPracticeTotalAfterPenalty)
        thisExp.nextEntry()

        ok = instruction_screen(
            f"Good job!\n\n"
            f"You earned {visualPracticeTotalAfterPenalty}p\n"
            f"in total during practice.",
            showPiggy=False,
            textPos=[0, 0.04],
            requiredPresses=2
        )
        if not ok:
            return


    if RUN_EYE_TRACKING_PRACTICE:




        repeatEyeInstruction = True

        while repeatEyeInstruction:

            ok = instruction_screen(
                "Each round starts with the piggy bank sound playing. "
                "Wait until you see + before you can shake it.",
                showPiggy=False,
                textPos=[0, 0.04]
            )
            if not ok:
                return

            ok = instruction_screen(
                "Before each round, look at the middle.\n\n"
                "The round starts only when\n"
                "you are looking there.",
                showPiggy=False,
                textPos=[0, 0.04]
            )
            if not ok:
                return

            ok = instruction_screen(
                "After a round starts, try not to look away.\n\n"
                "If you look away, we will set up\n"
                "the eye tracker again.",
                showPiggy=False,
                textPos=[0, 0.04]
            )
            if not ok:
                return

            eyeQuizPassed = true_false_quiz_screen(
                "eyeInstructionQuiz",
                [
                    "I should keep holding the three marked keys during the task.",
                    "When I see ×, I should wait and not press yet.",
                    "When I see +, I should press the response key and keep looking at the middle."
                ]
            )

            if eyeQuizPassed is None:
                return

            if eyeQuizPassed:
                repeatEyeInstruction = False
            else:
                repeatEyeInstruction = True

        ok = instruction_screen(
            "We will now set up the eye tracker.\n\n"
            "Then the 6 practice rounds will start.",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return

        ok = fixation_only_space_screen()
        if not ok:
            return

        ok = run_eye_calibration("before_eye_practice")
        if not ok:
            thisExp.addData('before_eye_practice_calibration_ok', False)
            thisExp.nextEntry()
            if thisExp.status == FINISHED:
                return
        else:
            thisExp.addData('before_eye_practice_calibration_ok', True)
            thisExp.nextEntry()

        ok = start_eye_recording("eye_practice")
        if not ok and EYETRACKER_BACKEND.lower() != 'mousegaze':
            return

        ok = show_post_calibration_grey_screen("before_eye_practice")
        if not ok:
            return

        if EYETRACKER_BACKEND.lower() == 'mousegaze':
            try:
                gazeMouse.setPos((0, 0))
            except Exception:
                pass

        routineTimer.reset()


        def show_practice_error(where, err):
            try:
                thisExp.addData('practice_eye_error_where', where)
                thisExp.addData('practice_eye_error_text', repr(err))
                thisExp.nextEntry()
            except Exception:
                pass

            errorText = visual.TextStim(
                win=win,
                name='practiceEyeErrorText',
                text=(
                    'The task could not continue.\n\n'
                    'Please let the researcher know.\n\n'
                    'Press SPACE to close.'
                ),
                font='Arial', pos=[0, CENTRAL_TEXT_MID_Y], height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP, color='white', colorSpace='rgb'
            )
            spaceWasDown = vk_down(0x20)
            while True:
                spaceDown = vk_down(0x20)
                errorText.draw()
                if spaceDown and not spaceWasDown:
                    break
                if vk_down(0x1B):
                    break
                spaceWasDown = spaceDown
                win.flip()
            routineTimer.reset()





        def handle_practice_gaze_break(trialNum, phase):





            thisExp.addData('practice_gazeBreak_trial', trialNum)
            thisExp.addData('practice_gazeBreak_phase', phase)
            thisExp.addData('practice_gazeBreak_time', globalClock.getTime(format='float'))
            thisExp.addData('practice_gazeBreak_action', 'restart_without_recalibration')
            thisExp.addData('practice_gazeBreak_recalibrationTriggered', False)
            thisExp.nextEntry()
            tracker_event(
                "practice_gaze_break",
                trial=trialNum,
                phase=phase,
                action='restart_without_recalibration'
            )

            try:
                CueSound.stop()
            except Exception:
                pass
            try:
                ClickSound.stop()
            except Exception:
                pass

            warningText = visual.TextStim(
                win=win,
                name='practiceGazeBreakWarningText',
                text=(
                    "Please keep looking at the middle of the screen.\n\n"
                    "You looked away during the round.\n\n"
                    "This practice round will now start again."
                ),
                font='Arial',
                pos=[0, CENTRAL_TEXT_MID_Y],
                height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP,
                color='white',
                colorSpace='rgb'
            )

            routineTimer.reset()
            while routineTimer.getTime() < 2.0:
                warningText.draw()
                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return False
                win.flip()

            routineTimer.reset()
            return True


        def run_practice_fixation_with_gaze(trialNum):
            ok = wait_for_gaze_to_start_trial('practice', blockNum=None, trialNum=trialNum)
            if ok is None:
                return None

            baselineDur = py_random.uniform(1.3, 1.7)
            fixTotalDur = 0.5 + baselineDur

            routineTimer.reset()
            fixationTiming = start_phase_on_next_flip(
                "practice_phase_start",
                trial=trialNum,
                phase="fixation",
                baselineDur=f"{baselineDur:.6f}",
                fixTotalDur=f"{fixTotalDur:.6f}",
            )
            gazeBreakMonitor = new_gaze_break_monitor()
            while routineTimer.getTime() < fixTotalDur:
                circle_fix1.draw()
                circle_fix2.draw()
                fix_.draw()

                if sustained_gaze_break(gazeBreakMonitor):
                    thisExp.addData('practice_gazeBreak_baselineDur', baselineDur)
                    thisExp.addData('practice_gazeBreak_fixTotalDur', fixTotalDur)
                    log_sustained_gaze_break('practice', gazeBreakMonitor, 'fixation', trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            thisExp.addData('practice_trial', trialNum)
            thisExp.addData('practice_baselineDur', baselineDur)
            thisExp.addData('practice_fixTotalDur', fixTotalDur)
            thisExp.addData('practice_baselineStartGlobal', fixationTiming['onset_global'])
            tracker_event("practice_phase_end", trial=trialNum, phase="fixation")
            routineTimer.reset()
            return {'timing': fixationTiming}


        def show_practice_early_press_warning(trialNum, pressCount):
            nonlocal eyePracticePenaltyPence
            penaltyPence = max(1, int(pressCount))
            eyePracticePenaltyPence += penaltyPence
            thisExp.addData('practice_earlyPressBeforePlus_trial', trialNum)
            thisExp.addData('practice_earlyPressCount', penaltyPence)
            thisExp.addData('practice_earlyPressPenaltyPence', penaltyPence)
            thisExp.addData('practice_totalPenaltyPence', eyePracticePenaltyPence)
            thisExp.nextEntry()
            tracker_event(
                "practice_early_press_penalty",
                trial=trialNum,
                pressCount=penaltyPence,
                penaltyPence=penaltyPence,
            )

            lossText = '1 penny' if penaltyPence == 1 else f'{penaltyPence} pence'
            warningStim = visual.TextStim(
                win=win,
                name='practiceEarlyPressWarningText',
                text=(
                    "Please wait until the symbol changes to + before pressing.\n\n"
                    f"You pressed {penaltyPence} time{'s' if penaltyPence != 1 else ''} during × and lost {lossText}.\n\n"
                    "Each press during × loses 1 pence.\n\n"
                    "Press SPACE to start this practice round again."
                ),
                font='Arial',
                pos=[0, CENTRAL_TEXT_MID_Y],
                height=TASK_TEXT_HEIGHT,
                wrapWidth=CENTRAL_TEXT_WRAP,
                color='white',
                colorSpace='rgb'
            )
            spaceWasDown = vk_down(0x20)
            while True:
                warningStim.draw()
                spaceDown = vk_down(0x20)
                if spaceDown and not spaceWasDown:
                    routineTimer.reset()
                    return True
                spaceWasDown = spaceDown
                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return False
                win.flip()


        def run_practice_cue_with_gaze(cueFileForTrial, trialNum, trialRow=None):
            trialCueSound = make_trial_cue_sound(
                cueFileForTrial,
                name=f'practiceCueSound_{trialNum}'
            )

            played = False
            cueTiming = None
            clear_response_key_events()
            routineTimer.reset()
            start_phase_on_next_flip(
                "practice_phase_start",
                trial=trialNum,
                phase="cue",
                cueFile=cueFileForTrial,
            )
            gazeBreakMonitor = new_gaze_break_monitor()
            while routineTimer.getTime() < 1.4:
                circle_cue1.draw()
                circle_cue2.draw()
                cue_.draw()

                if not played:
                    cueTiming = schedule_sound_on_next_flip(
                        trialCueSound,
                        'practice_cue',
                        trial=trialNum,
                        cueFile=cueFileForTrial,
                    )
                    played = True

                early_events = get_response_keypresses()
                if early_events:
                    trialCueSound.stop()
                    early_global_times = []
                    early_hold_ok = []
                    early_keys = []
                    for early_press_number, key_event in enumerate(early_events, start=1):
                        global_time = press_global_time(key_event)
                        holdOK = hold_keys_ok(holdVKCodes)
                        early_global_times.append(global_time)
                        early_hold_ok.append(bool(holdOK))
                        early_keys.append(responseKey)
                        tracker_event(
                            "practice_early_press_before_plus",
                            trial=trialNum,
                            cueFile=cueFileForTrial,
                            earlyPressNumber=early_press_number,
                            localTime=f"{global_time - (cueTiming['audio_planned_onset_global'] if cueTiming else global_time):.6f}",
                            globalTime=f"{global_time:.6f}",
                            holdOK=int(bool(holdOK)),
                            responseKey=responseKey,
                        )

                    thisExp.addData('practice_trial', trialNum)
                    thisExp.addData('practice_cueFile', cueFileForTrial)
                    thisExp.addData('practice_earlyPressBeforePlus', True)
                    thisExp.addData('practice_earlyPressOccurred', True)
                    thisExp.addData('practice_earlyPressCount', len(early_events))
                    thisExp.addData('practice_earlyPressGlobalTimes', early_global_times)
                    thisExp.addData('practice_earlyPressHoldOK', early_hold_ok)
                    thisExp.addData('practice_earlyPressKeys', early_keys)
                    row_for_log = trialRow if isinstance(trialRow, dict) else {}
                    thisExp.addData('practice_conditionIndex', row_for_log.get('conditionIndex', ''))
                    thisExp.addData('practice_cueIdentity', row_for_log.get('cueIdentity', ''))
                    thisExp.nextEntry()
                    routineTimer.reset()
                    return ('EARLY_PRESS', len(early_events))

                if sustained_gaze_break(gazeBreakMonitor):
                    trialCueSound.stop()
                    log_sustained_gaze_break('practice', gazeBreakMonitor, 'cue', trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    trialCueSound.stop()
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("practice_phase_end", trial=trialNum, phase="cue")
            thisExp.addData('practice_trial', trialNum)
            thisExp.addData('practice_cueFile', cueFileForTrial)
            if cueTiming is not None:
                thisExp.addData('practice_cueVisualOnsetGlobal', cueTiming['visual_onset_global'])
                thisExp.addData('practice_cueAudioPlannedOnsetGlobal', cueTiming['audio_planned_onset_global'])
                thisExp.addData('practice_cueAudioPlannedOnsetPTB', cueTiming['audio_planned_onset_ptb'])
                thisExp.addData('practice_cueAudioScheduledWithPTB', cueTiming['audio_scheduled_with_ptb'])
            row_for_log = trialRow if isinstance(trialRow, dict) else {}
            thisExp.addData('practice_conditionIndex', row_for_log.get('conditionIndex', ''))
            thisExp.addData('practice_cueIdentity', row_for_log.get('cueIdentity', ''))
            routineTimer.reset()
            return trialCueSound


        def run_practice_click_with_gaze(
            fbFileForTrial,
            FRForTrial,
            magForTrial,
            trialNum,
            cueSoundToStop=None
        ):
            rewardSoundFile = resolve_reward_file(fbFileForTrial)

            clickDur = py_random.uniform(4.0, 6.0)
            FRForTrial = int(FRForTrial)
            magForTrial = float(magForTrial)

            nextThresh = FRForTrial
            lastCount = 0
            validPressCount = 0
            invalidPressCount = 0
            validPressRTs = []
            validPressGlobalTimes = []
            validPressKeys = []
            invalidPressRTs = []
            invalidPressGlobalTimes = []
            invalidPressKeys = []
            rewardTriggerPressRTs = []
            rewardTriggerPressGlobalTimes = []
            rewardAudioPlannedOnsetGlobals = []
            rewardAudioPlannedOnsetsPTB = []
            rewardThresholds = []
            rewardNumbers = []
            rewardSoundObjects = []

            def stop_reward_sounds():
                for rewardSound in rewardSoundObjects:
                    try:
                        rewardSound.stop()
                    except Exception:
                        pass

            clear_response_key_events()
            routineTimer.reset()
            start_phase_on_next_flip(
                "practice_phase_start",
                trial=trialNum,
                phase="click",
                clickDur=f"{clickDur:.6f}",
                FR=FRForTrial,
                fbFile=fbFileForTrial,
            )
            plusTiming = mark_visual_on_next_flip('practice_plus_visual_onset', trial=trialNum)
            gazeBreakMonitor = new_gaze_break_monitor()
            while routineTimer.getTime() < clickDur:
                for keyEvent in get_response_keypresses():
                    globalTime = press_global_time(keyEvent)
                    plus_reference = plusTiming['visual_onset_global'] or globalTime
                    localTime = globalTime - plus_reference
                    holdOK = hold_keys_ok(holdVKCodes)
                    if holdOK:
                        validPressCount += 1
                        validPressKeys.append(responseKey)
                        validPressRTs.append(localTime)
                        validPressGlobalTimes.append(globalTime)
                    else:
                        invalidPressCount += 1
                        invalidPressRTs.append(localTime)
                        invalidPressGlobalTimes.append(globalTime)
                        invalidPressKeys.append(responseKey)
                        tracker_event(
                            "practice_invalid_press",
                            trial=trialNum,
                            invalidPressNumber=invalidPressCount,
                            localTime=f"{localTime:.6f}",
                            globalTime=f"{globalTime:.6f}",
                        )

                count = validPressCount
                if count > lastCount:
                    while count >= nextThresh:
                        rewardThreshold = nextThresh
                        rewardPressIndex = rewardThreshold - 1
                        rewardLocalT = validPressRTs[rewardPressIndex]
                        rewardGlobalT = validPressGlobalTimes[rewardPressIndex]
                        rewardNumber = len(rewardTriggerPressRTs) + 1
                        rewardSound = make_lab_sound(
                            rewardSoundFile,
                            secs=-1,
                            stereo=True,
                            hamming=True,
                            name=f'practiceRewardSound_{trialNum}_{rewardNumber}',
                        )
                        rewardSound.setVolume(REWARD_SOUND_VOLUME)
                        rewardSoundObjects.append(rewardSound)
                        rewardTiming = schedule_sound_on_next_flip(
                            rewardSound,
                            'practice_reward_sound',
                            visual_marker=False,
                            trial=trialNum,
                            rewardNumber=rewardNumber,
                            threshold=rewardThreshold,
                            pressGlobalTime=f"{rewardGlobalT:.6f}",
                            overlapEnabled=int(REWARD_SOUND_OVERLAP_ENABLED),
                        )

                        rewardTriggerPressRTs.append(rewardLocalT)
                        rewardTriggerPressGlobalTimes.append(rewardGlobalT)
                        rewardAudioPlannedOnsetGlobals.append(rewardTiming['audio_planned_onset_global'])
                        rewardAudioPlannedOnsetsPTB.append(rewardTiming['audio_planned_onset_ptb'])
                        rewardThresholds.append(rewardThreshold)
                        rewardNumbers.append(rewardNumber)
                        nextThresh += FRForTrial
                lastCount = count

                circle_click1.draw()
                circle_click2.draw()
                click_.draw()

                if sustained_gaze_break(gazeBreakMonitor):
                    if cueSoundToStop is not None:
                        try:
                            cueSoundToStop.stop()
                        except Exception:
                            pass
                    stop_reward_sounds()
                    thisExp.addData('practice_gazeBreak_clickDur', clickDur)
                    thisExp.addData('practice_gazeBreak_validPressCount_beforeRestart', validPressCount)
                    thisExp.addData('practice_gazeBreak_invalidPressCount_beforeRestart', invalidPressCount)
                    thisExp.addData('practice_gazeBreak_invalidPressRTs_beforeRestart', invalidPressRTs)
                    thisExp.addData('practice_gazeBreak_invalidPressGlobalTimes_beforeRestart', invalidPressGlobalTimes)
                    thisExp.addData('practice_gazeBreak_rewardTriggerPressRTs_beforeRestart', rewardTriggerPressRTs)
                    thisExp.addData('practice_gazeBreak_rewardTriggerPressGlobalTimes_beforeRestart', rewardTriggerPressGlobalTimes)
                    thisExp.addData('practice_gazeBreak_rewardAudioPlannedOnsetGlobals_beforeRestart', rewardAudioPlannedOnsetGlobals)
                    thisExp.addData('practice_gazeBreak_rewardAudioPlannedOnsetsPTB_beforeRestart', rewardAudioPlannedOnsetsPTB)
                    log_sustained_gaze_break('practice', gazeBreakMonitor, 'click', trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    if cueSoundToStop is not None:
                        try:
                            cueSoundToStop.stop()
                        except Exception:
                            pass
                    stop_reward_sounds()
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("practice_phase_end", trial=trialNum, phase="click")
            if cueSoundToStop is not None:
                try:
                    cueSoundToStop.stop()
                except Exception:
                    pass

            nRewards = math.floor(validPressCount / FRForTrial)
            earnedThisTrial = nRewards * magForTrial

            thisExp.addData('practice_trial', trialNum)
            thisExp.addData('practice_plusVisualOnsetGlobal', plusTiming['visual_onset_global'])
            thisExp.addData('practice_clickDur', clickDur)
            thisExp.addData('practice_FR', FRForTrial)
            thisExp.addData('practice_mag', magForTrial)
            thisExp.addData('practice_fbFile', fbFileForTrial)
            thisExp.addData('practice_validPressCount', validPressCount)
            thisExp.addData('practice_invalidPressCount', invalidPressCount)
            thisExp.addData('practice_invalidPressRTs', invalidPressRTs)
            thisExp.addData('practice_invalidPressGlobalTimes', invalidPressGlobalTimes)
            thisExp.addData('practice_invalidPressKeys', invalidPressKeys)
            thisExp.addData('practice_validPressKeys', validPressKeys)
            thisExp.addData('practice_validPressRTs', validPressRTs)
            thisExp.addData('practice_validPressGlobalTimes', validPressGlobalTimes)
            thisExp.addData('practice_rewardTriggerPressRTs', rewardTriggerPressRTs)
            thisExp.addData('practice_rewardTriggerPressGlobalTimes', rewardTriggerPressGlobalTimes)
            thisExp.addData('practice_rewardAudioPlannedOnsetGlobals', rewardAudioPlannedOnsetGlobals)
            thisExp.addData('practice_rewardAudioPlannedOnsetsPTB', rewardAudioPlannedOnsetsPTB)
            thisExp.addData('practice_rewardThresholds', rewardThresholds)
            thisExp.addData('practice_rewardNumbers', rewardNumbers)
            thisExp.addData('practice_nRewards', nRewards)
            thisExp.addData('practice_earnedThisTrial', earnedThisTrial)

            routineTimer.reset()
            return {
                'validPressCount': validPressCount,
                'validPressRTs': validPressRTs,
                'validPressGlobalTimes': validPressGlobalTimes,
                'invalidPressCount': invalidPressCount,
                'invalidPressRTs': invalidPressRTs,
                'invalidPressGlobalTimes': invalidPressGlobalTimes,
                'rewardTriggerPressRTs': rewardTriggerPressRTs,
                'rewardTriggerPressGlobalTimes': rewardTriggerPressGlobalTimes,
                'rewardAudioPlannedOnsetGlobals': rewardAudioPlannedOnsetGlobals,
                'rewardAudioPlannedOnsetsPTB': rewardAudioPlannedOnsetsPTB,
                'rewardSoundObjects': rewardSoundObjects,
                'nRewards': nRewards,
                'earnedThisTrial': earnedThisTrial,
                'plusTiming': plusTiming,
            }


        def run_practice_iti_with_gaze(trialNum):
            itiDur = py_random.uniform(1.5, 2.5)

            routineTimer.reset()
            itiTiming = start_phase_on_next_flip(
                "practice_phase_start",
                trial=trialNum,
                phase="iti",
                itiDur=f"{itiDur:.6f}",
            )
            while routineTimer.getTime() < itiDur:
                circle_ITI1.draw()
                circle_ITI2.draw()

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("practice_phase_end", trial=trialNum, phase="iti")
            thisExp.addData('practice_trial', trialNum)
            thisExp.addData('practice_itiDur', itiDur)
            thisExp.addData('practice_itiStartGlobal', itiTiming['onset_global'])
            routineTimer.reset()
            return {'timing': itiTiming}


        def run_one_practice_trial_with_gaze_restart(trialRow, trialNum):
            attemptNum = 0

            while True:
                attemptNum += 1
                thisExp.addData('practice_trialAttempt_trial', trialNum)
                thisExp.addData('practice_trialAttempt_number', attemptNum)
                thisExp.nextEntry()
                tracker_event("practice_trial_start", trial=trialNum, attempt=attemptNum)

                ok = run_practice_fixation_with_gaze(trialNum)
                if ok is None:
                    return None
                if ok == 'GAZE_BREAK':
                    if not handle_practice_gaze_break(trialNum, 'fixation'):
                        return None
                    continue

                cueResult = run_practice_cue_with_gaze(
                    trialRow['cueFile'],
                    trialNum,
                    trialRow=trialRow
                )
                if cueResult is None:
                    return None
                if cueResult == 'GAZE_BREAK':
                    if not handle_practice_gaze_break(trialNum, 'cue'):
                        return None
                    continue
                if isinstance(cueResult, tuple) and cueResult[0] == 'EARLY_PRESS':
                    if not show_practice_early_press_warning(trialNum, pressCount=cueResult[1]):
                        return None
                    continue

                clickResult = run_practice_click_with_gaze(
                    fbFileForTrial=trialRow['fbFile'],
                    FRForTrial=trialRow['FR'],
                    magForTrial=trialRow['mag'],
                    trialNum=trialNum,
                    cueSoundToStop=cueResult
                )
                if clickResult is None:
                    return None
                if clickResult == 'GAZE_BREAK':
                    if not handle_practice_gaze_break(trialNum, 'click'):
                        return None
                    continue

                ok = run_practice_iti_with_gaze(trialNum)
                if ok is None:
                    return None

                thisExp.addData('practice_trialCompletedAttempt', attemptNum)
                thisExp.nextEntry()
                return clickResult


        try:
            practiceRows = []
            for row in participantMappedMainRows:
                practiceRow = dict(row)
                practiceRow['cueFile'] = eyePracticeCueFiles[practiceRow['cueIdentity']]
                practiceRow['cueVersion'] = EYE_PRACTICE_CUE_VERSION
                practiceRows.append(practiceRow)
            py_random.shuffle(practiceRows)

            for practiceTrialNum, practiceTrialRow in enumerate(practiceRows, start=1):
                practiceResult = run_one_practice_trial_with_gaze_restart(
                    trialRow=practiceTrialRow,
                    trialNum=practiceTrialNum
                )

                if practiceResult is None:
                    return

                totalEarned += practiceResult['earnedThisTrial']
        except Exception as err:
            show_practice_error('eye_practice_6_trials', err)
            return

        stop_eye_recording("eye_practice_end")

    if RUN_MAIN_TASK_SETUP_AND_CALIBRATION:


        practiceTotalPence = int(round(totalEarned - eyePracticePenaltyPence))
        thisExp.addData('practice_totalEarnedBeforePenalty', totalEarned)
        thisExp.addData('practice_totalPenaltyPence', eyePracticePenaltyPence)
        thisExp.addData('practice_totalEarnedAfterPenalty', practiceTotalPence)
        thisExp.nextEntry()

        ok = instruction_screen(
            f"You have finished the practice.\n\n"
            f"Across the 6 practice rounds,\n"
            f"you earned {practiceTotalPence}p in total.",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return

        ok = instruction_screen(
            "Good job!\n\n"
            "The main task is next. You will not see your earnings during this part.\n\n"
            "Respond as before. This part will last about 13 minutes, with two short breaks along the way.",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return

        ok = instruction_screen(
            "Before the main task,\n"
            "we will set up the eye tracker again.\n\n"
            "Please try your best to keep looking\n"
            "at the middle of the screen.\n\n"
            "",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return

        ok = run_eye_calibration("before_main_task")
        if not ok:
            return


    formalTotalEarned = 0.0
    formalMinimumPossibleEarnings = 0.0
    formalMaximumPossibleEarnings = 0.0
    formalRawEarningRatio = 0.0
    formalEarningRatio = 0.0
    formalBonusGBP = 1.0
    finalPence = 0

    if RUN_MAIN_TASK:





        def run_formal_fixation(blockNum, trialNum):
            ok = wait_for_gaze_to_start_trial('main', blockNum=blockNum, trialNum=trialNum)
            if ok is None:
                return None

            baselineDur = py_random.uniform(1.3, 1.7)
            fixTotalDur = 0.5 + baselineDur

            routineTimer.reset()
            fixationTiming = start_phase_on_next_flip(
                "main_phase_start",
                block=blockNum,
                trial=trialNum,
                phase="fixation",
                baselineDur=f"{baselineDur:.6f}",
                fixTotalDur=f"{fixTotalDur:.6f}",
            )
            gazeBreakMonitor = new_gaze_break_monitor()

            while routineTimer.getTime() < fixTotalDur:
                circle_fix1.draw()
                circle_fix2.draw()
                fix_.draw()

                if sustained_gaze_break(gazeBreakMonitor):
                    thisExp.addData('main_gazeBreak_baselineDur', baselineDur)
                    thisExp.addData('main_gazeBreak_fixTotalDur', fixTotalDur)
                    log_sustained_gaze_break('main', gazeBreakMonitor, 'fixation', blockNum=blockNum, trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("main_phase_end", block=blockNum, trial=trialNum, phase="fixation")
            thisExp.addData('main_block', blockNum)
            thisExp.addData('main_trial', trialNum)
            thisExp.addData('main_baselineDur', baselineDur)
            thisExp.addData('main_fixTotalDur', fixTotalDur)
            thisExp.addData('main_baselineStartGlobal', fixationTiming['onset_global'])

            routineTimer.reset()
            return {'timing': fixationTiming}


        def run_formal_cue(cueFileForTrial, blockNum, trialNum):

            trialCueSound = make_trial_cue_sound(
                cueFileForTrial,
                name=f'mainCueSound_{blockNum}_{trialNum}'
            )

            played = False
            cueTiming = None
            earlyPressRTs = []
            earlyPressGlobalTimes = []
            earlyPressHoldOK = []
            earlyPressKeys = []

            def save_early_press_data():
                thisExp.addData('main_earlyPressCount', len(earlyPressRTs))
                thisExp.addData('main_earlyPressRTs', earlyPressRTs)
                thisExp.addData('main_earlyPressGlobalTimes', earlyPressGlobalTimes)
                thisExp.addData('main_earlyPressHoldOK', earlyPressHoldOK)
                thisExp.addData('main_earlyPressKeys', earlyPressKeys)
                thisExp.addData('main_earlyPressOccurred', bool(earlyPressRTs))

            clear_response_key_events()
            routineTimer.reset()
            start_phase_on_next_flip(
                "main_phase_start",
                block=blockNum,
                trial=trialNum,
                phase="cue",
                cueFile=cueFileForTrial,
            )
            gazeBreakMonitor = new_gaze_break_monitor()

            while routineTimer.getTime() < 1.4:
                circle_cue1.draw()
                circle_cue2.draw()
                cue_.draw()

                if not played:
                    cueTiming = schedule_sound_on_next_flip(
                        trialCueSound,
                        'main_cue',
                        block=blockNum,
                        trial=trialNum,
                        cueFile=cueFileForTrial,
                    )
                    played = True

                for keyEvent in get_response_keypresses():
                    globalTime = press_global_time(keyEvent)
                    cue_reference = cueTiming['audio_planned_onset_global'] if cueTiming else globalTime
                    localTime = globalTime - cue_reference
                    holdOK = hold_keys_ok(holdVKCodes)
                    earlyPressRTs.append(localTime)
                    earlyPressGlobalTimes.append(globalTime)
                    earlyPressHoldOK.append(bool(holdOK))
                    earlyPressKeys.append(responseKey)
                    save_early_press_data()
                    tracker_event(
                        "main_early_press_before_plus",
                        block=blockNum,
                        trial=trialNum,
                        earlyPressNumber=len(earlyPressRTs),
                        localTime=f"{localTime:.6f}",
                        globalTime=f"{globalTime:.6f}",
                        holdOK=int(bool(holdOK)),
                        responseKey=responseKey,
                    )

                if sustained_gaze_break(gazeBreakMonitor):
                    trialCueSound.stop()
                    save_early_press_data()
                    log_sustained_gaze_break('main', gazeBreakMonitor, 'cue', blockNum=blockNum, trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    trialCueSound.stop()
                    save_early_press_data()
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("main_phase_end", block=blockNum, trial=trialNum, phase="cue")
            thisExp.addData('main_block', blockNum)
            thisExp.addData('main_trial', trialNum)
            thisExp.addData('main_cueFile', cueFileForTrial)
            if cueTiming is not None:
                thisExp.addData('main_cueVisualOnsetGlobal', cueTiming['visual_onset_global'])
                thisExp.addData('main_cueAudioPlannedOnsetGlobal', cueTiming['audio_planned_onset_global'])
                thisExp.addData('main_cueAudioPlannedOnsetPTB', cueTiming['audio_planned_onset_ptb'])
                thisExp.addData('main_cueAudioScheduledWithPTB', cueTiming['audio_scheduled_with_ptb'])
            save_early_press_data()

            routineTimer.reset()
            return {
                'sound': trialCueSound,
                'timing': cueTiming or {},
                'early_press_count': len(earlyPressRTs),
                'early_press_rts': earlyPressRTs,
                'early_press_global_times': earlyPressGlobalTimes,
            }


        def run_formal_click(
            fbFileForTrial,
            FRForTrial,
            magForTrial,
            blockNum,
            trialNum,
            cueSoundToStop=None
        ):
            rewardSoundFile = resolve_reward_file(fbFileForTrial)

            clickDur = py_random.uniform(4.0, 6.0)
            FRForTrial = int(FRForTrial)
            magForTrial = float(magForTrial)

            nextThresh = FRForTrial
            lastCount = 0
            validPressCount = 0
            invalidPressCount = 0
            validPressRTs = []
            validPressGlobalTimes = []
            validPressKeys = []
            invalidPressRTs = []
            invalidPressGlobalTimes = []
            invalidPressKeys = []
            rewardTriggerPressRTs = []
            rewardTriggerPressGlobalTimes = []
            rewardAudioPlannedOnsetGlobals = []
            rewardAudioPlannedOnsetsPTB = []
            rewardThresholds = []
            rewardNumbers = []
            rewardSoundObjects = []

            def stop_reward_sounds():
                for rewardSound in rewardSoundObjects:
                    try:
                        rewardSound.stop()
                    except Exception:
                        pass

            clear_response_key_events()
            routineTimer.reset()
            start_phase_on_next_flip(
                "main_phase_start",
                block=blockNum,
                trial=trialNum,
                phase="click",
                clickDur=f"{clickDur:.6f}",
                FR=FRForTrial,
                fbFile=fbFileForTrial,
            )
            plusTiming = mark_visual_on_next_flip(
                'main_plus_visual_onset', block=blockNum, trial=trialNum
            )
            gazeBreakMonitor = new_gaze_break_monitor()

            while routineTimer.getTime() < clickDur:
                for keyEvent in get_response_keypresses():
                    globalTime = press_global_time(keyEvent)
                    plus_reference = plusTiming['visual_onset_global'] or globalTime
                    localTime = globalTime - plus_reference
                    holdOK = hold_keys_ok(holdVKCodes)
                    if holdOK:
                        validPressCount += 1
                        validPressKeys.append(responseKey)
                        validPressRTs.append(localTime)
                        validPressGlobalTimes.append(globalTime)
                    else:
                        invalidPressCount += 1
                        invalidPressRTs.append(localTime)
                        invalidPressGlobalTimes.append(globalTime)
                        invalidPressKeys.append(responseKey)
                        tracker_event(
                            "main_invalid_press",
                            block=blockNum,
                            trial=trialNum,
                            invalidPressNumber=invalidPressCount,
                            localTime=f"{localTime:.6f}",
                            globalTime=f"{globalTime:.6f}",
                        )

                count = validPressCount
                if count > lastCount:
                    while count >= nextThresh:
                        rewardThreshold = nextThresh
                        rewardPressIndex = rewardThreshold - 1
                        rewardLocalT = validPressRTs[rewardPressIndex]
                        rewardGlobalT = validPressGlobalTimes[rewardPressIndex]
                        rewardNumber = len(rewardTriggerPressRTs) + 1
                        rewardSound = make_lab_sound(
                            rewardSoundFile,
                            secs=-1,
                            stereo=True,
                            hamming=True,
                            name=f'mainRewardSound_{blockNum}_{trialNum}_{rewardNumber}',
                        )
                        rewardSound.setVolume(REWARD_SOUND_VOLUME)
                        rewardSoundObjects.append(rewardSound)
                        rewardTiming = schedule_sound_on_next_flip(
                            rewardSound,
                            'main_reward_sound',
                            visual_marker=False,
                            block=blockNum,
                            trial=trialNum,
                            rewardNumber=rewardNumber,
                            threshold=rewardThreshold,
                            pressGlobalTime=f"{rewardGlobalT:.6f}",
                            overlapEnabled=int(REWARD_SOUND_OVERLAP_ENABLED),
                        )

                        rewardTriggerPressRTs.append(rewardLocalT)
                        rewardTriggerPressGlobalTimes.append(rewardGlobalT)
                        rewardAudioPlannedOnsetGlobals.append(rewardTiming['audio_planned_onset_global'])
                        rewardAudioPlannedOnsetsPTB.append(rewardTiming['audio_planned_onset_ptb'])
                        rewardThresholds.append(rewardThreshold)
                        rewardNumbers.append(rewardNumber)
                        nextThresh += FRForTrial
                lastCount = count

                circle_click1.draw()
                circle_click2.draw()
                click_.draw()

                if sustained_gaze_break(gazeBreakMonitor):
                    if cueSoundToStop is not None:
                        try:
                            cueSoundToStop.stop()
                        except Exception:
                            pass
                    stop_reward_sounds()
                    thisExp.addData('main_gazeBreak_clickDur', clickDur)
                    thisExp.addData('main_gazeBreak_validPressCount_beforeRestart', validPressCount)
                    thisExp.addData('main_gazeBreak_invalidPressCount_beforeRestart', invalidPressCount)
                    thisExp.addData('main_gazeBreak_invalidPressRTs_beforeRestart', invalidPressRTs)
                    thisExp.addData('main_gazeBreak_invalidPressGlobalTimes_beforeRestart', invalidPressGlobalTimes)
                    thisExp.addData('main_gazeBreak_rewardTriggerPressRTs_beforeRestart', rewardTriggerPressRTs)
                    thisExp.addData('main_gazeBreak_rewardTriggerPressGlobalTimes_beforeRestart', rewardTriggerPressGlobalTimes)
                    thisExp.addData('main_gazeBreak_rewardAudioPlannedOnsetGlobals_beforeRestart', rewardAudioPlannedOnsetGlobals)
                    thisExp.addData('main_gazeBreak_rewardAudioPlannedOnsetsPTB_beforeRestart', rewardAudioPlannedOnsetsPTB)
                    log_sustained_gaze_break('main', gazeBreakMonitor, 'click', blockNum=blockNum, trialNum=trialNum)
                    routineTimer.reset()
                    return 'GAZE_BREAK'

                if vk_down(0x1B):
                    if cueSoundToStop is not None:
                        try:
                            cueSoundToStop.stop()
                        except Exception:
                            pass
                    stop_reward_sounds()
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("main_phase_end", block=blockNum, trial=trialNum, phase="click")
            if cueSoundToStop is not None:
                try:
                    cueSoundToStop.stop()
                except Exception:
                    pass

            nRewards = math.floor(validPressCount / FRForTrial)
            earnedThisTrial = nRewards * magForTrial


            minimumPossibleThisTrial = magForTrial if FRForTrial == 1 else 0.0
            maximumPossibleThisTrial = (10.0 * clickDur * magForTrial) / FRForTrial

            thisExp.addData('main_block', blockNum)
            thisExp.addData('main_trial', trialNum)
            thisExp.addData('main_plusVisualOnsetGlobal', plusTiming['visual_onset_global'])
            thisExp.addData('main_clickDur', clickDur)
            thisExp.addData('main_FR', FRForTrial)
            thisExp.addData('main_mag', magForTrial)
            thisExp.addData('main_fbFile', fbFileForTrial)
            thisExp.addData('main_validPressCount', validPressCount)
            thisExp.addData('main_invalidPressCount', invalidPressCount)
            thisExp.addData('main_invalidPressRTs', invalidPressRTs)
            thisExp.addData('main_invalidPressGlobalTimes', invalidPressGlobalTimes)
            thisExp.addData('main_invalidPressKeys', invalidPressKeys)
            thisExp.addData('main_validPressKeys', validPressKeys)
            thisExp.addData('main_validPressRTs', validPressRTs)
            thisExp.addData('main_validPressGlobalTimes', validPressGlobalTimes)
            thisExp.addData('main_rewardTriggerPressRTs', rewardTriggerPressRTs)
            thisExp.addData('main_rewardTriggerPressGlobalTimes', rewardTriggerPressGlobalTimes)
            thisExp.addData('main_rewardAudioPlannedOnsetGlobals', rewardAudioPlannedOnsetGlobals)
            thisExp.addData('main_rewardAudioPlannedOnsetsPTB', rewardAudioPlannedOnsetsPTB)
            thisExp.addData('main_rewardThresholds', rewardThresholds)
            thisExp.addData('main_rewardNumbers', rewardNumbers)
            thisExp.addData('main_nRewards', nRewards)
            thisExp.addData('main_earnedThisTrial', earnedThisTrial)
            thisExp.addData('main_minimumPossibleEarningsThisTrial', minimumPossibleThisTrial)
            thisExp.addData('main_maximumPossibleEarningsThisTrial', maximumPossibleThisTrial)

            routineTimer.reset()
            return {
                "validPressCount": validPressCount,
                "validPressRTs": validPressRTs,
                "validPressGlobalTimes": validPressGlobalTimes,
                "invalidPressCount": invalidPressCount,
                "invalidPressRTs": invalidPressRTs,
                "invalidPressGlobalTimes": invalidPressGlobalTimes,
                "rewardTriggerPressRTs": rewardTriggerPressRTs,
                "rewardTriggerPressGlobalTimes": rewardTriggerPressGlobalTimes,
                "rewardAudioPlannedOnsetGlobals": rewardAudioPlannedOnsetGlobals,
                "rewardAudioPlannedOnsetsPTB": rewardAudioPlannedOnsetsPTB,
                "rewardSoundObjects": rewardSoundObjects,
                "nRewards": nRewards,
                "earnedThisTrial": earnedThisTrial,
                "minimumPossibleEarningsThisTrial": minimumPossibleThisTrial,
                "maximumPossibleEarningsThisTrial": maximumPossibleThisTrial,
                "plusTiming": plusTiming,
                "clickDur": clickDur,
                "FR": FRForTrial,
                "mag": magForTrial,
                "fbFile": fbFileForTrial,
            }


        def run_formal_iti(blockNum, trialNum):
            itiDur = py_random.uniform(1.5, 2.5)

            routineTimer.reset()
            itiTiming = start_phase_on_next_flip(
                "main_phase_start",
                block=blockNum,
                trial=trialNum,
                phase="iti",
                itiDur=f"{itiDur:.6f}",
            )

            while routineTimer.getTime() < itiDur:
                circle_ITI1.draw()
                circle_ITI2.draw()

                if vk_down(0x1B):
                    thisExp.status = FINISHED
                    endExperiment(thisExp, win=win)
                    return None

                win.flip()

            tracker_event("main_phase_end", block=blockNum, trial=trialNum, phase="iti")
            thisExp.addData('main_block', blockNum)
            thisExp.addData('main_trial', trialNum)
            thisExp.addData('main_itiDur', itiDur)
            thisExp.addData('main_itiStartGlobal', itiTiming['onset_global'])

            routineTimer.reset()
            return {'timing': itiTiming}


        def run_formal_trial(trialRow, cueFileForTrial, cueIdentity, conditionIndex, blockNum, trialNum, cueVersionForTrial=None):
            attemptNum = 0

            while True:
                attemptNum += 1
                thisExp.addData('main_trialAttempt_block', blockNum)
                thisExp.addData('main_trialAttempt_trial', trialNum)
                thisExp.addData('main_trialAttempt_number', attemptNum)
                thisExp.nextEntry()
                send_tracker_message(
                    f"TRIALID MAIN_B{blockNum}_T{trialNum}_A{attemptNum}"
                )
                tracker_event(
                    "main_trial_start",
                    block=blockNum,
                    trial=trialNum,
                    attempt=attemptNum,
                    conditionIndex=conditionIndex,
                    cueIdentity=cueIdentity
                )

                fixationResult = run_formal_fixation(blockNum, trialNum)
                if fixationResult is None:
                    return None
                if fixationResult == 'GAZE_BREAK':
                    send_tracker_message("TRIAL_RESULT 1")
                    if not handle_formal_gaze_break(blockNum, trialNum, 'fixation'):
                        return None
                    continue

                cueResult = run_formal_cue(
                    cueFileForTrial,
                    blockNum,
                    trialNum
                )
                if cueResult is None:
                    return None
                if cueResult == 'GAZE_BREAK':
                    send_tracker_message("TRIAL_RESULT 1")
                    if not handle_formal_gaze_break(blockNum, trialNum, 'cue'):
                        return None
                    continue

                clickResult = run_formal_click(
                    fbFileForTrial=trialRow['fbFile'],
                    FRForTrial=trialRow['FR'],
                    magForTrial=trialRow['mag'],
                    blockNum=blockNum,
                    trialNum=trialNum,
                    cueSoundToStop=cueResult['sound']
                )
                if clickResult is None:
                    return None
                if clickResult == 'GAZE_BREAK':
                    send_tracker_message("TRIAL_RESULT 1")
                    if not handle_formal_gaze_break(blockNum, trialNum, 'click'):
                        return None
                    continue

                itiResult = run_formal_iti(blockNum, trialNum)
                if itiResult is None:
                    return None

                cueVersion = cueVersionForTrial if cueVersionForTrial is not None else blockNum
                thisExp.addData('main_conditionIndex', conditionIndex)
                thisExp.addData('main_cueIdentity', cueIdentity)
                thisExp.addData('main_blockVersion', cueVersion)
                thisExp.addData('main_cueVersion', cueVersion)
                thisExp.addData('main_cueFileForTrial', cueFileForTrial)
                thisExp.addData('main_trialCompletedAttempt', attemptNum)

                cueTiming = cueResult.get('timing', {})
                plusTiming = clickResult.get('plusTiming', {})
                write_main_trial_record({
                    'participant_id': expInfo.get('participant', ''),
                    'session_id': expInfo.get('session', ''),
                    'task_date': expInfo.get('date', ''),
                    'block': blockNum,
                    'trial': trialNum,
                    'completed_attempt': attemptNum,
                    'condition_index': conditionIndex,
                    'cue_identity': cueIdentity,
                    'cue_version': cueVersion,
                    'cue_file': cueFileForTrial,
                    'FR': int(trialRow['FR']),
                    'magnitude_pence': float(trialRow['mag']),
                    'feedback_file': trialRow['fbFile'],
                    'baseline_start_global': fixationResult.get('timing', {}).get('onset_global', ''),
                    'cue_visual_onset_global': cueTiming.get('visual_onset_global', ''),
                    'cue_audio_planned_onset_global': cueTiming.get('audio_planned_onset_global', ''),
                    'cue_audio_planned_onset_ptb': cueTiming.get('audio_planned_onset_ptb', ''),
                    'cue_audio_scheduled_with_ptb': cueTiming.get('audio_scheduled_with_ptb', ''),
                    'plus_visual_onset_global': plusTiming.get('visual_onset_global', ''),
                    'iti_start_global': itiResult.get('timing', {}).get('onset_global', ''),
                    'click_duration_s': clickResult.get('clickDur', ''),
                    'early_press_count': cueResult.get('early_press_count', ''),
                    'early_press_rts_s': cueResult.get('early_press_rts', ''),
                    'early_press_global_times_s': cueResult.get('early_press_global_times', ''),
                    'valid_press_count': clickResult.get('validPressCount', ''),
                    'valid_press_rts_s': clickResult.get('validPressRTs', ''),
                    'valid_press_global_times_s': clickResult.get('validPressGlobalTimes', ''),
                    'invalid_press_count': clickResult.get('invalidPressCount', ''),
                    'invalid_press_rts_s': clickResult.get('invalidPressRTs', ''),
                    'invalid_press_global_times_s': clickResult.get('invalidPressGlobalTimes', ''),
                    'reward_count': clickResult.get('nRewards', ''),
                    'reward_trigger_press_rts_s': clickResult.get('rewardTriggerPressRTs', ''),
                    'reward_trigger_press_global_times_s': clickResult.get('rewardTriggerPressGlobalTimes', ''),
                    'reward_audio_planned_onsets_global_s': clickResult.get('rewardAudioPlannedOnsetGlobals', ''),
                    'reward_audio_planned_onsets_ptb_s': clickResult.get('rewardAudioPlannedOnsetsPTB', ''),
                    'earned_pence': clickResult.get('earnedThisTrial', ''),
                    'minimum_possible_earnings_pence': clickResult.get('minimumPossibleEarningsThisTrial', ''),
                    'maximum_possible_earnings_pence': clickResult.get('maximumPossibleEarningsThisTrial', ''),
                })

                send_tracker_message("TRIAL_RESULT 0")

                thisExp.nextEntry()

                return clickResult




        formalTotalEarned = 0.0
        reset_display_timing_log()

        ok = start_eye_recording("main_task")
        if not ok:
            thisExp.addData('main_task_eye_recording_started', False)
            thisExp.addData('main_task_aborted_reason', 'eye_recording_failed')
            thisExp.nextEntry()
            tracker_event('main_task_aborted', reason='eye_recording_failed')
            endExperiment(thisExp, win=win)
            return
        else:
            ok = show_post_calibration_grey_screen("before_main_task")
            if not ok:
                return

        for blockNum in range(1, MAIN_N_BLOCKS + 1):

            blockRowsWithIndex = list(enumerate(mainConditionRows))
            py_random.shuffle(blockRowsWithIndex)

            thisExp.addData('main_blockStarted', blockNum)
            thisExp.nextEntry()
            tracker_event("main_block_start", block=blockNum)

            for trialIndex, rowInfo in enumerate(blockRowsWithIndex, start=1):
                conditionIndex, trialRow = rowInfo

                cueIdentity = conditionToCueIdentity[conditionIndex]

                cueVersionForBlock = MAIN_CUE_BLOCK_VERSIONS[(blockNum - 1) % len(MAIN_CUE_BLOCK_VERSIONS)]
                cueFileForTrial = mainCueFiles[(cueIdentity, cueVersionForBlock)]

                trialResult = run_formal_trial(
                    trialRow=trialRow,
                    cueFileForTrial=cueFileForTrial,
                    cueIdentity=cueIdentity,
                    conditionIndex=conditionIndex,
                    blockNum=blockNum,
                    trialNum=trialIndex,
                    cueVersionForTrial=cueVersionForBlock
                )

                if trialResult is None:
                    return

                formalTotalEarned += trialResult["earnedThisTrial"]
                formalMinimumPossibleEarnings += trialResult["minimumPossibleEarningsThisTrial"]
                formalMaximumPossibleEarnings += trialResult["maximumPossibleEarningsThisTrial"]

            tracker_event("main_block_end", block=blockNum)
            thisExp.addData('main_blockFinished', blockNum)
            thisExp.addData('main_totalEarnedSoFar', formalTotalEarned)
            thisExp.nextEntry()




            if blockNum in MAIN_REST_AFTER_BLOCKS:
                stop_eye_recording(f"break_after_block_{blockNum}")

                completedPart = MAIN_REST_AFTER_BLOCKS.index(blockNum) + 1
                totalParts = len(MAIN_REST_AFTER_BLOCKS) + 1
                ok = instruction_screen(
                    "Good job!\n\n"
                    f"You have completed part {completedPart} of {totalParts}.\n\n"
                    "You can take a short rest now.\n\n"
                    "When you are ready, please use the bell\n"
                    "to call the researcher.\n\n"
                    "The researcher will set up the eye tracker\n"
                    "again before you continue.",
                    showPiggy=False,
                    textPos=[0, 0.04]
                )
                if not ok:
                    return

                ok = run_eye_calibration(f"after_break_block_{blockNum}")
                if not ok:
                    return

                ok = start_eye_recording(f"main_task_after_break_block_{blockNum}")
                if not ok:
                    thisExp.addData('main_task_eye_recording_started', False)
                    thisExp.addData('main_task_aborted_reason', f'eye_recording_failed_after_break_block_{blockNum}')
                    thisExp.nextEntry()
                    tracker_event('main_task_aborted', reason=f'eye_recording_failed_after_break_block_{blockNum}')
                    endExperiment(thisExp, win=win)
                    return

                ok = show_post_calibration_grey_screen(
                    f"after_break_block_{blockNum}"
                )
                if not ok:
                    return


        stop_eye_recording("main_task_end")
        save_display_timing_summary('main_task')

        finalPence = int(round(formalTotalEarned))


        bonusDenominator = formalMaximumPossibleEarnings - formalMinimumPossibleEarnings
        if bonusDenominator > 0:
            formalRawEarningRatio = (
                (formalTotalEarned - formalMinimumPossibleEarnings) / bonusDenominator
            )
        else:
            formalRawEarningRatio = 0.0

        formalEarningRatio = max(0.0, min(1.0, formalRawEarningRatio))
        formalBonusGBP = (formalEarningRatio * 2.0) + 1.0

        thisExp.addData('mainTask_actualEarningsPence', formalTotalEarned)
        thisExp.addData('mainTask_minimumPossibleEarningsPence', formalMinimumPossibleEarnings)
        thisExp.addData('mainTask_maximumPossibleEarningsPence', formalMaximumPossibleEarnings)
        thisExp.addData('mainTask_bonusRatePressesPerSecond', 10.0)
        thisExp.addData('mainTask_earningRatioRaw', formalRawEarningRatio)
        thisExp.addData('mainTask_earningRatio', formalEarningRatio)
        thisExp.addData('mainTask_bonusGBP', formalBonusGBP)
        thisExp.addData('mainTask_bonusGBPRoundedToPence', round(formalBonusGBP, 2))
        thisExp.nextEntry()

        ok = instruction_screen(
            "Good job!\n\n"
            "You have finished the main task.",
            showPiggy=False,
            textPos=[0, 0.04]
        )
        if not ok:
            return





    def get_condition_metric(row):

        try:
            magValue = float(row['mag'])
            frValue = float(row['FR'])
        except Exception:
            magValue = float(row.get('magnitude', 0))
            frValue = float(row.get('fixedRatio', 1))

        if frValue == 0:
            return 0.0
        return magValue / frValue


    def get_understanding_cue_label(cueIdentity):

        return CUE_IDENTITY_LABELS.get(cueIdentity, f"Sound {cueIdentity}")


    def find_understanding_cue_image_file(cueIdentity, cueFile):

        baseNames = list(CUE_IDENTITY_IMAGE_LABELS.get(cueIdentity, []))

        stem = os.path.splitext(os.path.basename(str(cueFile)))[0]
        stemNoVersion = re.sub(r"_?v[0-9]+$", "", stem, flags=re.IGNORECASE)
        for baseName in [stem, stemNoVersion, re.sub(r"^[0-9]+", "", stemNoVersion)]:
            baseName = baseName.strip()
            if baseName:
                baseNames.append(baseName)

        imageRoots = [
            baseDir,
            os.path.join(baseDir, "stimuli"),
            os.path.join(baseDir, "stimuli_eq"),
            os.path.join(baseDir, "images"),
            os.path.join(baseDir, "cue_images"),
        ]

        seenCandidates = set()
        for baseName in baseNames:
            for extension in [".png", ".jpg", ".jpeg", ".bmp"]:
                for fileName in [baseName + extension, baseName.lower() + extension, baseName.title() + extension]:
                    candidateKey = fileName.lower()
                    if candidateKey in seenCandidates:
                        continue
                    seenCandidates.add(candidateKey)
                    for imageRoot in imageRoots:
                        imagePath = os.path.join(imageRoot, fileName)
                        if os.path.exists(imagePath):
                            return imagePath

        return None


    def prepare_understanding_sound(cueFile, optionPosition, cueIdentity):

        CueSound.stop()
        CueSound.setSound(cueFile, secs=-1, hamming=True)
        CueSound.setVolume(1.0)
        CueSound.seek(0)
        return schedule_sound_on_next_flip(
            CueSound,
            'understanding_option_sound',
            optionPosition=optionPosition,
            cueIdentity=cueIdentity,
            cueFile=cueFile,
        )


    def understanding_response_screen(questionText, firstInfo, secondInfo):

        optionInfos = [firstInfo, secondInfo]
        optionPositions = [[-0.235, -0.025], [0.235, -0.025]]
        optionKeys = ['x', 'm']

        questionStim = visual.TextStim(
            win=win,
            name='understandingQuestionText',
            text=questionText,
            font='Arial',
            pos=[0, 0.245],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )
        promptStim = visual.TextStim(
            win=win,
            name='understandingResponsePrompt',
            text=(
                "Press X to select Sound 1 and hear it.  "
                "Press M to select Sound 2 and hear it.\n"
                "Press SPACE to choose the highlighted sound."
            ),
            font='Arial',
            pos=[0, BOTTOM_PROMPT_Y],
            height=TASK_TEXT_HEIGHT,
            wrapWidth=BOTTOM_PROMPT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        optionStims = []
        for optionIndex, (_, optionPos) in enumerate(zip(optionInfos, optionPositions), start=1):
            boxStim = visual.Rect(
                win=win,
                name=f'understandingOptionBox_{optionIndex}',
                width=0.330,
                height=0.250,
                pos=optionPos,
                lineWidth=3,
                lineColor='grey',
                fillColor=None,
                colorSpace='named'
            )
            optionHeaderStim = visual.TextStim(
                win=win,
                name=f'understandingOptionHeader_{optionIndex}',
                text=f"Sound {optionIndex}",
                font='Arial',
                pos=optionPos,
                height=TASK_TEXT_HEIGHT,
                wrapWidth=0.300,
                color='white',
                colorSpace='rgb'
            )

            optionStims.append({
                'box': boxStim,
                'header': optionHeaderStim,
            })

        selectedPosition = None
        firstSelectionKey = ''
        firstSelectionRT = ''
        soundPlayCount = 0
        xWasDown = vk_down(VK_X)
        mWasDown = vk_down(VK_M)
        spaceWasDown = vk_down(0x20)
        responseClock = core.Clock()

        tracker_event(
            'understanding_response_phase_start',
            question=questionText,
            option1CueIdentity=firstInfo['cueIdentity'],
            option2CueIdentity=secondInfo['cueIdentity'],
        )

        while True:
            xDown = vk_down(VK_X)
            mDown = vk_down(VK_M)
            spaceDown = vk_down(0x20)

            selectedOptionIndex = None
            if xDown and not xWasDown:
                selectedOptionIndex = 0
            elif mDown and not mWasDown:
                selectedOptionIndex = 1

            if selectedOptionIndex is not None:
                selectedPosition = selectedOptionIndex + 1
                selectedInfo = optionInfos[selectedOptionIndex]
                soundPlayCount += 1
                prepare_understanding_sound(
                    selectedInfo['cueFile'],
                    optionPosition=selectedPosition,
                    cueIdentity=selectedInfo['cueIdentity'],
                )

                if not firstSelectionKey:
                    firstSelectionKey = optionKeys[selectedOptionIndex]
                    firstSelectionRT = responseClock.getTime()

                tracker_event(
                    'understanding_option_selected',
                    optionPosition=selectedPosition,
                    optionKey=optionKeys[selectedOptionIndex],
                    cueIdentity=selectedInfo['cueIdentity'],
                    cueFile=selectedInfo['cueFile'],
                )

            if spaceDown and not spaceWasDown and selectedPosition is not None:
                CueSound.stop()
                confirmationRT = responseClock.getTime()
                tracker_event(
                    'understanding_response_confirmed',
                    choicePosition=selectedPosition,
                    choiceKey=optionKeys[selectedPosition - 1],
                    confirmationRT=confirmationRT,
                )
                return {
                    'choicePosition': selectedPosition,
                    'key': optionKeys[selectedPosition - 1],
                    'confirmationKey': 'space',
                    'rt': confirmationRT,
                    'firstSelectionKey': firstSelectionKey,
                    'firstSelectionRT': firstSelectionRT,
                    'soundPlayCount': soundPlayCount,
                }

            xWasDown = xDown
            mWasDown = mDown
            spaceWasDown = spaceDown

            if vk_down(0x1B):
                CueSound.stop()
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return None

            questionStim.draw()

            for optionIndex, optionStimSet in enumerate(optionStims, start=1):
                optionStimSet['box'].lineColor = 'white' if selectedPosition == optionIndex else 'grey'
                optionStimSet['box'].draw()
                optionStimSet['header'].draw()

            promptStim.draw()
            win.flip()


    def understanding_continue_screen(mainText):

        mainStim = visual.TextStim(
            win=win,
            name='understandingContinueText',
            text=mainText + "\n\nPress SPACE to continue.",
            font='Arial',
            pos=[0, CENTRAL_TEXT_MID_Y],
            height=fitted_text_height(mainText + "\n\nPress SPACE to continue.", preferred=TASK_TEXT_HEIGHT, minimum=TASK_TEXT_MIN_HEIGHT, available_height=0.42),
            wrapWidth=CENTRAL_TEXT_WRAP,
            color='white',
            colorSpace='rgb'
        )

        spaceWasDown = vk_down(0x20)
        while True:
            mainStim.draw()

            spaceDown = vk_down(0x20)
            if spaceDown and not spaceWasDown:
                routineTimer.reset()
                return True

            spaceWasDown = spaceDown

            if vk_down(0x1B):
                thisExp.status = FINISHED
                endExperiment(thisExp, win=win)
                return False

            win.flip()


    def run_understanding_trial(blockNum, trialNum, sequenceTrialNum, pairInfo, askLarger):
        firstInfo, secondInfo = pairInfo

        question = (
            "Which piggy bank gives more money?"
            if askLarger else
            "Which piggy bank gives less money?"
        )
        response = understanding_response_screen(question, firstInfo, secondInfo)
        if response is None:
            return None

        firstMetric = firstInfo['metric']
        secondMetric = secondInfo['metric']

        if math.isclose(firstMetric, secondMetric, rel_tol=1e-9, abs_tol=1e-9):
            correctPosition = 0
            score = 1
        else:
            if askLarger:
                correctPosition = 1 if firstMetric > secondMetric else 2
            else:
                correctPosition = 1 if firstMetric < secondMetric else 2
            score = 1 if response['choicePosition'] == correctPosition else 0

        thisExp.addData('understanding_block', blockNum)
        thisExp.addData('understanding_trial', trialNum)
        thisExp.addData('understanding_sequenceTrial', sequenceTrialNum)
        thisExp.addData('understanding_question', 'larger' if askLarger else 'smaller')
        thisExp.addData('understanding_displayFormat', 'sound_number_options')
        thisExp.addData('understanding_option1Key', 'x')
        thisExp.addData('understanding_option2Key', 'm')
        thisExp.addData('understanding_firstConditionIndex', firstInfo['conditionIndex'])
        thisExp.addData('understanding_secondConditionIndex', secondInfo['conditionIndex'])
        thisExp.addData('understanding_firstCueIdentity', firstInfo['cueIdentity'])
        thisExp.addData('understanding_secondCueIdentity', secondInfo['cueIdentity'])
        thisExp.addData('understanding_firstCueFile', firstInfo['cueFile'])
        thisExp.addData('understanding_secondCueFile', secondInfo['cueFile'])
        thisExp.addData('understanding_firstCueImage', firstInfo['imagePath'])
        thisExp.addData('understanding_secondCueImage', secondInfo['imagePath'])
        thisExp.addData('understanding_firstCueLabel', firstInfo['labelText'])
        thisExp.addData('understanding_secondCueLabel', secondInfo['labelText'])
        thisExp.addData('understanding_firstFR', firstInfo['FR'])
        thisExp.addData('understanding_secondFR', secondInfo['FR'])
        thisExp.addData('understanding_firstMag', firstInfo['mag'])
        thisExp.addData('understanding_secondMag', secondInfo['mag'])
        thisExp.addData('understanding_firstMetric', firstMetric)
        thisExp.addData('understanding_secondMetric', secondMetric)
        thisExp.addData('understanding_correctPosition', correctPosition)
        thisExp.addData('understanding_choicePosition', response['choicePosition'])
        thisExp.addData('understanding_choiceKey', response['key'])
        thisExp.addData('understanding_confirmationKey', response['confirmationKey'])
        thisExp.addData('understanding_firstSelectionKey', response['firstSelectionKey'])
        thisExp.addData('understanding_firstSelectionRT', response['firstSelectionRT'])
        thisExp.addData('understanding_soundPlayCount', response['soundPlayCount'])
        thisExp.addData('understanding_sound2ResponseKey', 'm')
        thisExp.addData('understanding_rt', response['rt'])
        thisExp.addData('understanding_score', score)

        write_final_sound_check_bonus_record({
            'record_type': 'sound_check_trial',
            'participant_id': expInfo.get('participant', ''),
            'session_id': expInfo.get('session', ''),
            'task_date': expInfo.get('date', ''),
            'sound_check_enabled': bool(RUN_SOUND_CHECK),
            'sound_check_block': blockNum,
            'sound_check_trial': trialNum,
            'sound_check_sequence_trial': sequenceTrialNum,
            'sound_check_question': 'larger' if askLarger else 'smaller',
            'sound_check_display_format': 'sound_number_options',
            'option1_key': 'x',
            'option2_key': 'm',
            'option1_condition_index': firstInfo['conditionIndex'],
            'option2_condition_index': secondInfo['conditionIndex'],
            'option1_cue_identity': firstInfo['cueIdentity'],
            'option2_cue_identity': secondInfo['cueIdentity'],
            'option1_cue_file': firstInfo['cueFile'],
            'option2_cue_file': secondInfo['cueFile'],
            'option1_cue_image': firstInfo['imagePath'],
            'option2_cue_image': secondInfo['imagePath'],
            'option1_label': firstInfo['labelText'],
            'option2_label': secondInfo['labelText'],
            'option1_FR': firstInfo['FR'],
            'option2_FR': secondInfo['FR'],
            'option1_magnitude_pence': firstInfo['mag'],
            'option2_magnitude_pence': secondInfo['mag'],
            'option1_metric': firstMetric,
            'option2_metric': secondMetric,
            'correct_position': correctPosition,
            'choice_position': response['choicePosition'],
            'choice_key': response['key'],
            'confirmation_key': response['confirmationKey'],
            'first_selection_key': response['firstSelectionKey'],
            'first_selection_rt_s': response['firstSelectionRT'],
            'sound_play_count': response['soundPlayCount'],
            'response_rt_s': response['rt'],
            'score': score,
        })
        thisExp.nextEntry()

        return score


    def run_understanding_blocks():
        cueInfos = []
        for conditionIndex, conditionRow in enumerate(mainConditionRows):
            cueIdentity = conditionToCueIdentity[conditionIndex]
            cueFile = mainCueFiles[(cueIdentity, 1)]
            cueInfos.append({
                'conditionIndex': conditionIndex,
                'cueIdentity': cueIdentity,
                'cueFile': cueFile,
                'imagePath': find_understanding_cue_image_file(cueIdentity, cueFile),
                'labelText': get_understanding_cue_label(cueIdentity),
                'FR': int(conditionRow['FR']),
                'mag': float(conditionRow['mag']),
                'metric': get_condition_metric(conditionRow)
            })

        basePairs = []
        for firstIndex in range(len(cueInfos)):
            for secondIndex in range(firstIndex + 1, len(cueInfos)):
                basePairs.append((cueInfos[firstIndex], cueInfos[secondIndex]))

        scoredPairs = []
        tiedPairs = []
        for firstInfo, secondInfo in basePairs:
            if math.isclose(firstInfo['metric'], secondInfo['metric'], rel_tol=1e-9, abs_tol=1e-9):
                tiedPairs.append((firstInfo, secondInfo))
            elif firstInfo['metric'] < secondInfo['metric']:
                scoredPairs.append((firstInfo, secondInfo))
            else:
                scoredPairs.append((secondInfo, firstInfo))

        py_random.shuffle(scoredPairs)
        py_random.shuffle(tiedPairs)
        block1Pairs = []
        splitIndex = len(scoredPairs) // 2
        for pairIndex, (lowerInfo, higherInfo) in enumerate(scoredPairs):
            if pairIndex < splitIndex:
                block1Pairs.append((lowerInfo, higherInfo))
            else:
                block1Pairs.append((higherInfo, lowerInfo))
        block1Pairs.extend(tiedPairs)
        py_random.shuffle(block1Pairs)
        block2Pairs = [(secondInfo, firstInfo) for firstInfo, secondInfo in block1Pairs]

        def correct_side_counts(pairList):
            sound1 = 0
            sound2 = 0
            ties = 0
            for firstInfo, secondInfo in pairList:
                if math.isclose(firstInfo['metric'], secondInfo['metric'], rel_tol=1e-9, abs_tol=1e-9):
                    ties += 1
                elif firstInfo['metric'] > secondInfo['metric']:
                    sound1 += 1
                else:
                    sound2 += 1
            return sound1, sound2, ties

        block1Sound1N, block1Sound2N, block1TieN = correct_side_counts(block1Pairs)
        block2Sound1N, block2Sound2N, block2TieN = correct_side_counts(block2Pairs)
        thisExp.addData('understanding_pairCountPerBlock', len(basePairs))
        thisExp.addData('understanding_block1_correctSound1_n', block1Sound1N)
        thisExp.addData('understanding_block1_correctSound2_n', block1Sound2N)
        thisExp.addData('understanding_block1_tiedMetric_n', block1TieN)
        thisExp.addData('understanding_block2_correctSound1_n', block2Sound1N)
        thisExp.addData('understanding_block2_correctSound2_n', block2Sound2N)
        thisExp.addData('understanding_block2_tiedMetric_n', block2TieN)
        thisExp.addData('understanding_participantVisibleBlocks', 1)
        thisExp.addData('understanding_trialPresentation', 'continuous')
        thisExp.nextEntry()

        ok = understanding_continue_screen(
            "Next, there will be a short sound check.\n\n"
            "On each round, Sound 1 and Sound 2 will appear.\n"
            "Press X to select Sound 1 and hear it.\n"
            "Press M to select Sound 2 and hear it.\n"
            "Press SPACE to choose the highlighted sound.\n\n"
            "Choose the sound linked to the piggy bank that gives more money."
        )
        if not ok:
            return None

        allTrials = []
        for trialNum, pairInfo in enumerate(block1Pairs, start=1):
            allTrials.append((1, trialNum, pairInfo))
        for trialNum, pairInfo in enumerate(block2Pairs, start=1):
            allTrials.append((2, trialNum, pairInfo))

        allScores = []
        for sequenceTrialNum, (blockNum, trialNum, pairInfo) in enumerate(allTrials, start=1):
            score = run_understanding_trial(
                blockNum,
                trialNum,
                sequenceTrialNum,
                pairInfo,
                askLarger=True,
            )
            if score is None:
                return None
            allScores.append(score)

        nCorrect = allScores.count(1)
        nIncorrect = allScores.count(0)
        totalUnderstandingTrials = len(allScores)
        understandingAccuracy = nCorrect / totalUnderstandingTrials if totalUnderstandingTrials > 0 else 0

        thisExp.addData('understanding_totalTrials', totalUnderstandingTrials)
        thisExp.addData('understanding_totalCorrect', nCorrect)
        thisExp.addData('understanding_totalIncorrect', nIncorrect)
        thisExp.addData('understanding_accuracy', understandingAccuracy)

        write_final_sound_check_bonus_record({
            'record_type': 'sound_check_summary',
            'participant_id': expInfo.get('participant', ''),
            'session_id': expInfo.get('session', ''),
            'task_date': expInfo.get('date', ''),
            'sound_check_enabled': bool(RUN_SOUND_CHECK),
            'sound_check_total_trials': totalUnderstandingTrials,
            'sound_check_total_correct': nCorrect,
            'sound_check_total_incorrect': nIncorrect,
            'sound_check_accuracy': understandingAccuracy,
        })
        thisExp.nextEntry()

        return True


    if RUN_SOUND_CHECK:
        ok = run_understanding_blocks()
        if ok is None:
            return

    ok = understanding_continue_screen(
        "The task is now finished.\n\n"
        "Thank you very much."
    )
    if not ok:
        return

    thisExp.addData('mainTask_totalEarned', formalTotalEarned)
    thisExp.addData('mainTask_totalEarnedPenceRounded', finalPence)
    thisExp.addData('mainTask_actualEarningsPence', formalTotalEarned)
    thisExp.addData('mainTask_minimumPossibleEarningsPence', formalMinimumPossibleEarnings)
    thisExp.addData('mainTask_maximumPossibleEarningsPence', formalMaximumPossibleEarnings)
    thisExp.addData('mainTask_bonusRatePressesPerSecond', 10.0)
    thisExp.addData('mainTask_earningRatioRaw', formalRawEarningRatio)
    thisExp.addData('mainTask_earningRatio', formalEarningRatio)
    thisExp.addData('mainTask_bonusGBP', formalBonusGBP)
    thisExp.addData('mainTask_bonusGBPRoundedToPence', round(formalBonusGBP, 2))

    write_final_sound_check_bonus_record({
        'record_type': 'bonus_summary',
        'participant_id': expInfo.get('participant', ''),
        'session_id': expInfo.get('session', ''),
        'task_date': expInfo.get('date', ''),
        'sound_check_enabled': bool(RUN_SOUND_CHECK),
        'main_actual_earnings_pence': formalTotalEarned,
        'main_minimum_possible_earnings_pence': formalMinimumPossibleEarnings,
        'main_maximum_possible_earnings_pence': formalMaximumPossibleEarnings,
        'main_earning_ratio_raw': formalRawEarningRatio,
        'main_earning_ratio': formalEarningRatio,
        'main_bonus_GBP': formalBonusGBP,
        'main_bonus_GBP_rounded_to_pence': round(formalBonusGBP, 2),
    })
    thisExp.addData('task_finished_time', globalClock.getTime(format='float'))
    thisExp.nextEntry()

    if thisSession is not None:
        thisSession.sendExperimentData()

    endExperiment(thisExp, win=win)


def closeEyeTrackingData(thisExp):

    if getattr(thisExp, '_eyetracking_shutdown_done', False):
        return
    setattr(thisExp, '_eyetracking_shutdown_done', True)

    ioServer = getattr(deviceManager, 'ioServer', None)
    tracker = None
    try:
        if ioServer is not None:
            tracker = ioServer.devices.tracker
    except Exception:
        tracker = None
    if tracker is None and ioServer is not None:
        try:
            tracker = ioServer.getDevice('tracker')
        except Exception:
            tracker = None

    extraInfo = getattr(thisExp, 'extraInfo', {}) or {}
    expected_edf_file = extraInfo.get('eyelink_edf_file_expected', '')
    expected_edf_path = extraInfo.get('eyelink_edf_local_path_expected', '')
    expected_hdf5_path = extraInfo.get('iohub_hdf5_local_path_expected', '')

    try:
        thisExp.addData('eyetracking_shutdown_started', data.getDateStr())
        if expected_edf_file:
            thisExp.addData('eyelink_edf_file_expected', expected_edf_file)
        if expected_edf_path:
            thisExp.addData('eyelink_edf_local_path_expected', expected_edf_path)
        if expected_hdf5_path:
            thisExp.addData('iohub_hdf5_local_path_expected', expected_hdf5_path)
    except Exception:
        pass

    final_message = 'EVENT=experiment_end reason=normal_shutdown'
    try:
        if ioServer is not None and hasattr(ioServer, 'sendMessageEvent'):
            ioServer.sendMessageEvent(text=final_message)
    except Exception as e:
        try:
            thisExp.addData('iohub_final_message_error', repr(e))
        except Exception:
            pass
    try:
        if tracker is not None and hasattr(tracker, 'sendMessage'):
            tracker.sendMessage(final_message)
    except Exception as e:
        try:
            thisExp.addData('eyelink_final_message_error', repr(e))
        except Exception:
            pass

    if tracker is not None:
        try:
            tracker.setRecordingState(False)
            thisExp.addData('eyetracker_final_recording_state', 'stopped')
        except Exception as e:
            try:
                thisExp.addData('eyetracker_final_recording_stop_error', repr(e))
            except Exception:
                pass
        try:
            tracker.setConnectionState(False)
            thisExp.addData('eyelink_connection_closed_for_edf_transfer', True)
        except Exception as e:
            try:
                thisExp.addData('eyelink_connection_close_error', repr(e))
            except Exception:
                pass

    if ioServer is not None:
        try:
            ioServer.quit()
            thisExp.addData('iohub_server_closed', True)
        except Exception as e:
            try:
                thisExp.addData('iohub_server_close_error', repr(e))
            except Exception:
                pass
        try:
            deviceManager.ioServer = None
        except Exception:
            pass

    scan_dirs = getattr(thisExp, '_eye_data_scan_dirs', [_thisDir])
    initial_snapshot = getattr(thisExp, '_eye_data_initial_snapshot', {})
    launch_started_at = float(getattr(thisExp, '_iohub_launch_started_at', 0.0) or 0.0)
    data_dir, edf_dir, hdf5_dir = eye_data_output_dirs(thisExp)
    output_stem = os.path.basename(getattr(thisExp, 'dataFileName', make_eye_data_stem(getattr(thisExp, 'extraInfo', {}) or {})))

    found_edf_path = ''
    found_hdf5_path = ''
    moved_edf_path = ''
    moved_hdf5_path = ''

    for _ in range(200):
        changed_paths = changed_eye_data_candidates(scan_dirs, initial_snapshot, launch_started_at)
        edf_paths = []
        hdf5_paths = []
        for path in changed_paths:
            lower_name = os.path.basename(path).lower()
            if lower_name.endswith('.edf') or lower_name in ('et_data', 'et_data.edf'):
                edf_paths.append(path)
            elif lower_name.endswith(('.hdf5', '.h5')) or lower_name == 'et_data.hdf5':
                hdf5_paths.append(path)

        if edf_paths or hdf5_paths:
            if edf_paths:
                found_edf_path = max(edf_paths, key=lambda p: os.path.getmtime(p))
            if hdf5_paths:
                found_hdf5_path = max(hdf5_paths, key=lambda p: os.path.getmtime(p))
            break
        time.sleep(0.1)

    try:
        if found_edf_path:
            moved_edf_path = move_eye_data_file(found_edf_path, edf_dir, output_stem, '.edf')
    except Exception as e:
        try:
            thisExp.addData('eyelink_edf_move_error', repr(e))
        except Exception:
            pass

    try:
        if found_hdf5_path:
            moved_hdf5_path = move_eye_data_file(found_hdf5_path, hdf5_dir, output_stem, '.hdf5')
    except Exception as e:
        try:
            thisExp.addData('iohub_hdf5_move_error', repr(e))
        except Exception:
            pass

    try:
        thisExp.addData('eyelink_edf_transfer_found_local', bool(found_edf_path))
        thisExp.addData('eyelink_edf_transfer_local_path', found_edf_path)
        thisExp.addData('eyelink_edf_final_path', moved_edf_path)
        thisExp.addData('eyelink_edf_output_directory', edf_dir)
        thisExp.addData('iohub_hdf5_found_local', bool(found_hdf5_path))
        thisExp.addData('iohub_hdf5_local_path', found_hdf5_path)
        thisExp.addData('iohub_hdf5_final_path', moved_hdf5_path)
        thisExp.addData('iohub_hdf5_output_directory', hdf5_dir)
        thisExp.addData('eyetracking_shutdown_completed', data.getDateStr())
        thisExp.nextEntry()
    except Exception:
        pass

def saveData(thisExp):
    filename = getattr(thisExp, 'dataFileName', os.path.join(_thisDir, 'data', 'last_run'))
    try:
        thisExp.saveAsWideText(filename + '.csv', delim='auto')
    except Exception:
        pass
    try:
        thisExp.saveAsPickle(filename)
    except Exception:
        pass


def endExperiment(thisExp, win=None):
    if getattr(thisExp, 'currentRoutine', None) is not None:
        try:
            comps = thisExp.currentRoutine.getPlaybackComponents()
        except Exception:
            comps = []
        for comp in comps:
            try:
                comp.stop()
            except Exception:
                pass
    if win is not None:
        win.clearAutoDraw()
        win.flip()
    closeEyeTrackingData(thisExp)
    logging.console.setLevel(logging.WARNING)
    thisExp.status = FINISHED
    for fcn in runAtExit:
        fcn()
    logging.flush()


def quit(thisExp, win=None, thisSession=None):
    try:
        thisExp.abort()
    except Exception:
        pass
    closeEyeTrackingData(thisExp)
    if win is not None:
        win.flip()
        win.close()
    logging.flush()
    if thisSession is not None:
        thisSession.stop()
    core.quit()


if __name__ == '__main__':
    expInfo = showExpInfoDlg(expInfo=expInfo)
    thisExp = setupData(expInfo=expInfo)
    logFile = setupLogging(filename=thisExp.dataFileName)
    win = setupWindow(expInfo=expInfo)
    setupDevices(expInfo=expInfo, thisExp=thisExp, win=win)
    run(
        expInfo=expInfo,
        thisExp=thisExp,
        win=win,
        globalClock='float'
    )
    saveData(thisExp=thisExp)
    quit(thisExp=thisExp, win=win)

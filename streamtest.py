"""
Stream test:
Pull the video from the drone and display in cv2 window.
Optionally encode video and dump to file.
@author Saksham Sinha and Jonathan Byrne
@copyright 2018 see license file for details
"""
import av
import numpy
import tellopy
import cv2


def encode(frame, ovstream, output):
    """
    convert frames to packets and write to file
    """
    try:
        pkt = ovstream.encode(frame)
    except Exception as err:
        print("encoding failed{0}".format(err))

    if pkt is not None:
        try:
            output.mux(pkt)
        except Exception:
            print('mux failed: ' + str(pkt))
    return True


def main():
    # Set up tello streaming
    drone = tellopy.Tello()
    drone.log.set_level(2)
    drone.connect()
    drone.start_video()

    # container for processing the packets into frames
    container = av.open(drone.get_video_stream())
    video_st = container.streams.video[0]

    # stream and outputfile for video
    output = av.open('archive.mp4', 'w')
    ovstream = output.add_stream('mpeg4', video_st.rate)
    ovstream.pix_fmt = 'yuv420p'
    ovstream.width = video_st.width
    ovstream.height = video_st.height

    counter = 0
    save = True
    for packet in container.demux((video_st,)):
        for frame in packet.decode():
            # convert frame to cv2 image and show
            image = cv2.cvtColor(numpy.array(
                frame.to_image()), cv2.COLOR_RGB2BGR)
            cv2.imshow('frame', image)
            key = cv2.waitKey(1) & 0xFF

            # save initial 1300 frames
            if save:
                new_frame = av.VideoFrame(
                    width=frame.width, height=frame.height, format=frame.format.name)
                for i in range(len(frame.planes)):
                    new_frame.planes[i].update(frame.planes[i])
                encode(new_frame, ovstream, output)
                counter += 1
                print("Frames encoded:", counter)
                if counter > 300:
                    output.close()
                    save == False

if __name__ == '__main__':
    main()

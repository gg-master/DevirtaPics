import cv2

from devirta_pics.camera.camera import Camera


def main():
    cam: Camera = Camera()
    while cam.alive():

        ret, frame = cam.read()

        if not ret:
            continue

        # Display the resulting frame
        cv2.imshow('frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # After the loop release the cap object
    cam.stop()
    # Destroy all the windows
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()

import cv2
import mediapipe as mp
import pyautogui
import math
import time
import sys

class HandGestureController:
    def __init__(self):
        print("Initializing Hand Gesture Controller...")
        
        # Hands
        try:
            self.mp_hands = mp.solutions.hands
            self.mp_draw = mp.solutions.drawing_utils
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            )
            print("✓ MediaPipe Hands initialized")
        except Exception as e:
            print(f"ERROR initializing MediaPipe: {e}")
            raise
        
        # camera
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("ERROR: Could not open camera. Trying camera index 1...")
                self.cap = cv2.VideoCapture(1)
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print("✓ Camera initialized")
        except Exception as e:
            print(f"ERROR initializing camera: {e}")
            raise
        
        # Control state
        self.prev_gesture = None
        self.gesture_start_time = 0
        self.gesture_threshold = 0.3  
        
        
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01
        
    def count_fingers(self, landmarks):
        """Count extended fingers"""
        fingers = []
        
        
        if landmarks[4].x < landmarks[3].x:
            fingers.append(1)
        else:
            fingers.append(0)
            
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        for tip, pip in zip(finger_tips, finger_pips):
            if landmarks[tip].y < landmarks[pip].y:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers
    
    def get_distance(self, p1, p2):
        """Calculate distance between two points"""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    def detect_gesture(self, landmarks):
        """Detect specific hand gestures"""
        fingers = self.count_fingers(landmarks)
        finger_count = sum(fingers)
        
        # Accelerate
        if finger_count == 5:
            return "accelerate"
        
        # Fist Brake
        elif finger_count == 0:
            return "brake"
        
        # Index finger up - Shoot/Horn
        elif fingers == [0, 1, 0, 0, 0]:
            return "shoot"
        
        # v - Jump/Handbrake
        elif fingers == [0, 1, 1, 0, 0]:
            return "handbrake"
        
        # 3 fingers - change camera
        elif finger_count == 3:
            return "camera"
        
        # steering
        wrist = landmarks[0]
        middle_finger = landmarks[9]
        
        # tilt angle
        angle = math.atan2(middle_finger.y - wrist.y, middle_finger.x - wrist.x)
        angle_deg = math.degrees(angle)
        
        if angle_deg > -45 and angle_deg < 45 and finger_count >= 3:
            return "steer_left"
        
        elif (angle_deg > 135 or angle_deg < -135) and finger_count >= 3:
            return "steer_right"
        
        return "idle"
    
    def execute_gesture(self, gesture):
        """Execute keyboard commands based on gesture"""
        try:
            if self.prev_gesture and self.prev_gesture != gesture:
                if self.prev_gesture == "accelerate":
                    pyautogui.keyUp('w')
                elif self.prev_gesture == "brake":
                    pyautogui.keyUp('s')
                elif self.prev_gesture == "steer_left":
                    pyautogui.keyUp('a')
                elif self.prev_gesture == "steer_right":
                    pyautogui.keyUp('d')
            
            # Execute 
            if gesture == "accelerate":
                pyautogui.keyDown('w')
            elif gesture == "brake":
                pyautogui.keyDown('s')
            elif gesture == "shoot":
                pyautogui.press('space') 
            elif gesture == "handbrake":
                pyautogui.press('space')
            elif gesture == "camera":
                pyautogui.press('v')
            elif gesture == "steer_left":
                pyautogui.keyDown('a')
            elif gesture == "steer_right":
                pyautogui.keyDown('d')
            elif gesture == "idle":
                for key in ['w', 'a', 's', 'd']:
                    pyautogui.keyUp(key)
        except Exception as e:
            print(f"Error executing gesture: {e}")
    
    def draw_info(self, frame, gesture, finger_count):
        """Draw information on frame"""
        cv2.rectangle(frame, (10, 10), (400, 180), (0, 0, 0), -1)
        cv2.putText(frame, f"Gesture: {gesture}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Fingers: {finger_count}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        controls = [
            "5 Fingers: Accelerate (W)",
            "0 Fingers: Brake (S)",
            "Tilt Left/Right: Steer (A/D)",
            "Press 'Q' to Quit"
        ]
        
        y_pos = 100
        for control in controls:
            cv2.putText(frame, control, (20, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_pos += 20
    
    def run(self):
        """Main control loop"""
        print("\n" + "="*50)
        print("GTA V Hand Gesture Control - ACTIVE")
        print("="*50)
        print("\nGesture Controls:")
        print("Open palm (5 fingers): Accelerate (W)")
        print("Fist (0 fingers): Brake (S)")
        print("Index finger: Horn (Space)")
        print(" Peace sign: Handbrake (Space)")
        print("Tilt hand left: Steer left (A)")
        print("Tilt hand right: Steer right (D)")
        print("Three fingers: Change camera (V)")
        print(" Press 'Q' to quit")
        print("Move mouse to top-left corner for emergency stop")
        print("="*50 + "\n")
        
        frame_count = 0
        
        try:
            while True:
                success, frame = self.cap.read()
                if not success:
                    print("ERROR: Failed to read from camera")
                    break
                
                frame_count += 1
                
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                gesture = "idle"
                finger_count = 0
                
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(
                            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                        
                        # Detect gesture
                        gesture = self.detect_gesture(hand_landmarks.landmark)
                        fingers = self.count_fingers(hand_landmarks.landmark)
                        finger_count = sum(fingers)
                        
                        current_time = time.time()
                        if gesture != self.prev_gesture:
                            self.gesture_start_time = current_time
                        
                        if current_time - self.gesture_start_time > self.gesture_threshold:
                            self.execute_gesture(gesture)
                        
                        self.prev_gesture = gesture
                else:
                    self.execute_gesture("idle")
                    self.prev_gesture = None
                
                # Draw UI
                self.draw_info(frame, gesture, finger_count)
                
                # Display frame
                cv2.imshow("GTA V Hand Gesture Control", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    print("\nQuitting...")
                    break
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            print(f"\nERROR in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        print("Cleaning up...")
        
        # Release all keys
        try:
            for key in ['w', 'a', 's', 'd']:
                pyautogui.keyUp(key)
        except:
            pass
        
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("✓ Control system stopped safely.")

if __name__ == "__main__":
    try:
        controller = HandGestureController()
        controller.run()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        print("\nTroubleshooting steps:")
        print("1. pip uninstall mediapipe")
        print("2. pip install mediapipe==0.10.9")
        print("3. Restart your terminal/IDE")
        sys.exit(1)
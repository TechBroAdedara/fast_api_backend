Attendance Verification by Geolocation
______________________________________

This application is intended to provide schools with an efficient and faster way of verifying students attendance for classes. The manual method of attendance verification entails writing your name and matric number on a piece of paper and passing the piece of paper around the class until everyone has written out their names. This can prove to be quite cumbersome. There are a lot of times where the lecture finishes without students being able to put their attendance down on time. This leads to a rush-hour kind of situation where students want to put their names on the attendance quickly before the lecturer leaves the class. Sometimes the attendance sheet is passed around late into the class and then students are expected to line up to get their attendance down on the sheet. If their attendance is short of 75% of the whole semester in some schools, you won't be eligible to write the attendance. 

Now imagine that scenerio with 500 students! Yes you could say, more attendance sheets could be used to minimize traffic of getting their names down, but then it leads us to our second problem. The use of paper to store attendance figures. Paper can be quite dispensible, and could get lost, torn, or rumpled easily. And the solution suggesting that we use more papers would just multiply the problem of paper in the first place by some order of magnitude. 

So it is clear, there is a need to develop a more efficient, computerized system of taking attendance for students. There have been a number of methods tested and explored to implement a computerized attendance taking system. These include QR codes in class to indicate one's presence in the classroom. But the problem with this is that, a caring friend could just take a picture of this QR code and send it to their friend. And this friend not in the classroom could scan it, hereby indicating that they were in the classroom, when infact they were not.

Another solution that has been tested is the use of a code given to the students in the classroom by a teacher to the students. Then the students input the code into one program and verify their presence in the classroom. But once again, you can quite easily identify the problem with that. Another caring friend could easily send the code to their friend, just like the previous problem. 

The need to develop a foolproof system is obvious. This is where Attendance verification using Geolocation comes in. The concept is quite simple. The administrator sets up a geofence, and if a student is in that geofence for the duration of that class, his attendance is recorded for that class. The main thing that makes this method foolproof is that a student wouldn't be able to mimic his presence in that class when they are infact not in the class location. But this method needs to take into consideration the ease of use for both the student and the administrator (Lecturer for the class or the school).


## Implementation
______________

The application will be split into two places. The administrator account and the student account. 
The implementation of the application would also be split into two phases. The backend for geolocation and geofencing services, and then the interface.

## Application
______________
Administrator application: The admin would be responsible for setting the geofence for the class. They would be responsible for inputting the name for that class as well, and then informing the students that the geofence for that class is active at the moment. So students would be informed to go into the app and verify their attendance.

Student application: The student would be responsible for inputing his details into the application on the time of registration (which we would get to later). The details include, for example, Student's ID, Student's Name, Student's Department and College. The students would also be responsible for responding to the prompt to verify attendance for a particular class. 




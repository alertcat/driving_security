// ignore_for_file: file_names

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
// import 'dart:io';

import 'package:camera/camera.dart';
import 'package:des_frontend/GeocodingService.dart';
import 'package:des_frontend/MapDirectionService.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
// import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class CameraScreen extends StatefulWidget {
  // final CameraDescription camera;

  const CameraScreen({
    super.key,
    // required this.camera
  });

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  // late CameraController _controller;
  // late Future<void> _initializeControllerFuture;
  List<String> _directions = [];
  List<LatLng> _routePolyline = [];
  // Set default location
  LatLng _currentPostion = const LatLng(0, 0);
  late MapController _mapController;
  final TextEditingController _destinationController = TextEditingController();
  LatLng? _destination;

  double _screenWidth = 0.0;
  double _screenHeight = 0.0;

  // Eye tracking screen coordinates
  double gazeX = 0;
  double gazeY = 0;

  // OCR results
  String ocrResults = '';
  String restaurantName = '';
  Map<String, dynamic>? _restaurantInfo;
  double box_x1 = 1000;
  double box_x2 = 50;
  double box_y1 = 100;
  double box_y2 = 50;
  bool _doneUpdateBox = false;
  double box_pos_x = 0;
  double box_pos_y = 0;

  // Image data (Will be changed to video and live footage soon)
  Uint8List? _imageBytes;

  // Chatbox with Computer
  final BASE_URL = 'http://172.20.10.2:5000';
  final List<Map<String, String>> _chatMessages = []; // List of chat messages
  final TextEditingController _chatController =
      TextEditingController(); // Chat input controller

  // Websocket channel
  late WebSocketChannel channel;
  StreamSubscription? _webSocketSubscription;
  bool isFirstMessage = false;

  // Speech to text instance
  stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  String _recognizedText = '';
  String _destinationDetected = '';

  @override
  void initState() {
    super.initState();

    _connectToServer();
    _initializeSpeech();

    // _controller = CameraController(widget.camera, ResolutionPreset.veryHigh);
    // _initializeControllerFuture = _controller.initialize();
    _mapController = MapController();

    _startLocationUpdates();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Cache screen dimensions safely
    _screenWidth = MediaQuery.of(context).size.width;
    _screenHeight = MediaQuery.of(context).size.height;
  }

  void _connectToServer() {
    channel = WebSocketChannel.connect(Uri.parse('ws://localhost:5000'));
    print('Connecting to server');

    channel.ready.then((_) {
      print('WebSocket connection established');
    }).catchError((error) {
      print('Connection failed: $error');
    });

    _webSocketSubscription = channel.stream.listen((data) {
      // it is image data
      if (data is List<int>) {
        setState(() {
          _imageBytes = Uint8List.fromList(data);
        });
      } else if (data is String) {
        try {
          // Decode the raw string into a Map
          final decodedData = jsonDecode(data) as Map<String, dynamic>;

          // Check if it's a chat message
          if (decodedData['chat'] != null) {
            setState(() {
              _chatMessages.add(
                  {'sender': 'Com', 'text': decodedData['chat'].toString()});
            });
          }
          // Handle gaze and OCR data
          else {
            setState(() {
              double screenWidth = MediaQuery.of(context).size.width;
              double screenHeight = MediaQuery.of(context).size.height;

              // Use actual image dimensions from the server
              double imageWidth = decodedData['image_width'].toDouble();
              double imageHeight = decodedData['image_height'].toDouble();

              // Scale gaze coordinates
              gazeX =
                  (decodedData['x'] is num ? decodedData['x'].toDouble() : -1) /
                      imageWidth *
                      screenWidth;
              gazeY =
                  (decodedData['y'] is num ? decodedData['y'].toDouble() : -1) /
                      imageHeight *
                      screenHeight;

              // Handle OCR results
              if (decodedData.containsKey('ocr_results') &&
                  decodedData['ocr_results'] is List) {
                ocrResults = jsonEncode(decodedData['ocr_results']);
                List<dynamic> ocrList = jsonDecode(ocrResults);
                if (ocrList.isNotEmpty) {
                  restaurantName = ocrList[0]['text'];
                  box_x1 =
                      ocrList[0]['x1'].toDouble() / imageWidth * screenWidth;
                  box_y1 =
                      ocrList[0]['y1'].toDouble() / imageHeight * screenHeight;
                  box_x2 =
                      ocrList[0]['x2'].toDouble() / imageWidth * screenWidth;
                  box_y2 =
                      ocrList[0]['y2'].toDouble() / imageHeight * screenHeight;
                  print('Box x: ${(box_x1 + box_x2) / 2}');
                  print('Box y: ${(box_y1 + box_y2) / 2}');
                } else {
                  box_x1 = box_x2 = box_y1 = box_y2 = 0;
                }
              } else {
                ocrResults = '';
                box_x1 = box_x2 = box_y1 = box_y2 = 0;
              }
              print('Gaze X: $gazeX, Gaze Y: $gazeY');
              print("Restaurant Name: $restaurantName");
            });
          }
        } catch (e) {
          print("Error parsing data: $e");
        }
      } else {
        print('Unknown data type: $data');
      }
    }, onDone: () {
      print('Connection closed');
      Future.delayed(Duration(seconds: 1), _connectToServer); // Reconnect
    }, onError: (error) {
      print('Error: $error');
    });
  }

  Future<void> _sendMessage(String message) async {
    // Handle user input
    if (message.isNotEmpty) {
      setState(() {
        _chatMessages.add({'sender': 'You', 'text': message});
      });
      _chatController.clear();
    }

    // Handle API OUTPUT
    final url = Uri.parse('$BASE_URL/agent');

    // Define custom headers
    final headers = {
      'Content-Type': 'application/json', // Specify JSON data
      // 'Authorization': 'Bearer your-token-here', // Example auth header
      // 'Custom-Header': 'SomeValue', // Custom header
    };

    final body = jsonEncode({
      'longitude': _currentPostion.longitude,
      'latitude': _currentPostion.latitude,
    });
    print(
        "Current Position: ${_currentPostion.latitude}, ${_currentPostion.longitude}");

    try {
      final client = http.Client();
      final req = http.Request('POST', url);
      req.headers.addAll(headers);
      req.body = body;

      // Send the POST request and get streamed response
      final response = await client.send(req);

      // Check the response
      if (response.statusCode == 200) {
        print(
            'Success: ${response.stream.transform(utf8.decoder)}'); // Print the response

        await for (var chunk in response.stream.transform(utf8.decoder)) {
          final lines = chunk.split('\n');
          for (var line in lines) {
            if (line.trim().isNotEmpty) {
              // Add the string together
              if (mounted) {
                String firstWord = line.trim().split(" ")[0];
                String remainingText =
                    line.trim().split(" ").sublist(1).join(" ");
                if (firstWord == "User:") {
                  setState(() {
                    _chatMessages.add({
                      'sender': 'You',
                      'text': remainingText,
                    });
                  });
                  // isFirstMessage = false;
                } else {
                  setState(() {
                    _chatMessages.add({
                      'sender': 'Com',
                      'text': remainingText,
                    });
                  });
                }
                // setState(() {
                //   _chatMessages.add({'sender': 'Com', 'text': line.trim()});
                // });
              }
            }
          }
          // setState(() {
          //   isFirstMessage = true;
          // });
        }
      } else {
        print('Failed: ${response.statusCode} - ${response.statusCode}');
      }

      client.close();
    } catch (e) {
      print('Error: $e');
    }
  }

  void _initializeSpeech() async {
    bool available = await _speech.initialize();
    if (!available) {
      print("Speech-to-text not available");
      return;
    }
  }

  void _startListening() async {
    if (!_isListening) {
      setState(() {
        _isListening = true;
        _recognizedText = '';
        _destinationDetected = ''; // Reset only when starting a new session
      });

      _speech.listen(
        onResult: (result) {
          print("Recognized words: ${result.recognizedWords}"); // Debugging
          setState(() {
            _recognizedText = result.recognizedWords;
            _processSpeech(_recognizedText);
          });
        },
        listenFor: Duration(seconds: 5), // Listen for up to 5 seconds
        pauseFor: Duration(seconds: 3), // Pause after 3 seconds of silence
      );
      setState(() {
        _isListening = false;
      });
    }
  }

  void _stopListening() async {
    if (_isListening) {
      await _speech.stop();
      setState(() {
        _isListening = false;
        // Do not reset _destinationDetected here
      });
    }
  }

  void _processSpeech(String text) {
    if (text.toLowerCase().contains("go to")) {
      List<String> words = text.toLowerCase().split("go to");
      if (words.length > 1) {
        setState(() {
          _destinationDetected = words[1].trim();
        });
        print("Destination: $_destinationDetected");
        _searchDestination(); // Call search function
        // Do not call _stopListening() here
      }
    }
  }

  // Fetch restaurant info
  Future<void> _fetchRestaurantInfo(String name) async {
    // setState(() {
    //   _restaurantInfo = {
    //     "name": "Fong Seng Nasi Lemak",
    //     "rating": 4.1,
    //     "reviews": [
    //       {
    //         "author": "Emily Wong",
    //         "rating": 5,
    //         "text":
    //             "As the HR team managing staff meals at the remote Jurong Fishery Port, where food options are limited, we’re grateful for the exceptional service Fong Seng team has provided.\nYou’ve made it possible for us to offer delicious and balanced meals to our staff every day.\n\nThe white rice is always perfectly cooked — 粒粒分明, and the nasi lemak rice is a firm favorite.\nThe nasi lemak-style chili brings just the right amount of spice, while the chicken wings, crispy outside and juicy inside, never disappoint.\n\nBeyond nasi lemak, we also love the sambal sotong, curry chicken, sesame oil chicken, and sweet and sour fish, all of which offer excellent variety.\nThe sunny-side-up eggs are always a delight too — crispy at the edges, but with a perfectly runny yolk!\n\nOverall, the meals are well-balanced, with a good mix of carbs, fiber, and protein, ensuring our staff stay energized and satisfied.\nWe truly appreciate the great service and quality food Fong Seng provide!"
    //       }
    //     ]
    //   };
    // });

    // Define the URL of your Flask backend
    final url = Uri.parse('$BASE_URL/search_place');

    // Define custom headers
    final headers = {
      'Content-Type': 'application/json', // Specify JSON data
      // 'Authorization': 'Bearer your-token-here', // Example auth header
      // 'Custom-Header': 'SomeValue', // Custom header
    };

    final body = jsonEncode({
      'place': name,
      'longitude': _currentPostion.longitude,
      'latitude': _currentPostion.latitude,
    });

    try {
      // Send the POST request
      final response = await http.post(
        url,
        headers: headers,
        body: body,
      );

      // Check the response
      if (response.statusCode == 200) {
        print('Success: ${response.body}');
        _restaurantInfo = jsonDecode(response.body);
      } else {
        print('Failed: ${response.statusCode} - ${response.body}');
        _restaurantInfo = null;
      }
    } catch (e) {
      print('Error: $e');
    }
  }

  void _startLocationUpdates() async {
    // Updates the current location
    Position position = await getCurrentLocation();
    print(position.latitude);
    print(position.longitude);
    _updateLocation(position.latitude, position.longitude);

    // get destination location props (start location)
    Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.best, distanceFilter: 10),
    ).listen((Position position) {
      _updateLocation(position.latitude, position.longitude);
    });
  }

  void _updateLocation(double lat, double lng) {
    setState(() {
      _currentPostion = LatLng(lat, lng);
      // move the map to current position and zoom
      _mapController.move(_currentPostion, 15.0);
    });

    // _fetchDirections(lat, lng);
  }

  Future<void> _searchDestination() async {
    // String address = _destinationController.text;
    String address = _destinationDetected == ''
        ? _destinationController.text
        : _destinationDetected;
    if (address.isEmpty) return;

    try {
      LatLng destinationCoordinates =
          await Geocodingservice.getCoordinates(address);

      setState(() {
        _destination = destinationCoordinates;
      });
      _fetchDirections(_currentPostion.latitude, _currentPostion.longitude,
          _destination!.latitude, _destination!.longitude);
    } catch (e) {
      print("Error fetching location: $e");
    }
  }

  void _fetchDirections(
      double startLat, double startLng, double endLat, double endLng) async {
    try {
      List<String> directions = await Mapdirectionservice.getRealTimeDirection(
          startLat, startLng, endLat, endLng);
      List<LatLng> polyline = await Mapdirectionservice.getRoutePolyline();

      setState(() {
        _directions = directions;
        _routePolyline = polyline;
        // print(_directions);
      });
    } catch (e) {
      print("Error fetching directions: $e");
    }
  }

  @override
  void dispose() {
    // _controller.dispose();
    _chatController.dispose();
    _destinationController.dispose();
    _webSocketSubscription?.cancel();
    channel.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // appBar: AppBar(
      //   title: const Center(child: Text('Webcam Stream')),
      // ),
      body: Stack(fit: StackFit.expand, children: [
        // Positioned.fill(
        //   child: FutureBuilder<void>(
        //       future: _initializeControllerFuture,
        //       builder: (context, snapshot) {
        //         if (snapshot.connectionState == ConnectionState.done) {
        //           print("done");
        //           return CameraPreview(_controller);
        //         } else {
        //           return const Center(
        //             child: CircularProgressIndicator(),
        //           );
        //         }
        //       }),
        // ),
        if (_imageBytes != null)
          Positioned.fill(
            child: Image.memory(
              _imageBytes!,
              fit: BoxFit.fill,
              gaplessPlayback: true,
            ),
          )
        else
          const Center(
            child: CircularProgressIndicator(),
          ),

        // Gaze Tracking Overlay
        // Positioned(
        // left: gazeX.clamp(0, MediaQuery.of(context).size.width - 20),
        // top: gazeY.clamp(0, MediaQuery.of(context).size.height - 20),
        //   child: Container(
        //     width: 20,
        //     height: 20,
        //     decoration: BoxDecoration(
        //       color: Colors.red,
        //       borderRadius: BorderRadius.circular(10),
        //     ),
        //   ),
        // ),

        // Destination Input Box
        // Positioned(
        //   top: 40,
        //   left: 20,
        //   right: 20,
        //   child: Container(
        //     padding: const EdgeInsets.all(10),
        //     decoration: BoxDecoration(
        //       color: Colors.white.withOpacity(0.8),
        //       borderRadius: BorderRadius.circular(10),
        //     ),
        //     child: Row(
        //       children: [
        //         Expanded(
        //             child: TextField(
        //           controller: _destinationController,
        //           decoration: const InputDecoration(
        //             hintText: "Enter Destination",
        //             border: InputBorder.none,
        //           ),
        //         )),
        //         IconButton(
        //             onPressed: _searchDestination,
        //             icon: const Icon(Icons.search))
        //       ],
        //     ),
        //   ),
        // ),

        // Live Map Overlay (Bottom Left)
        Positioned(
            bottom: 20,
            left: 20,
            child: ClipRRect(
                borderRadius: BorderRadius.circular(15),
                child: Container(
                    width: 200,
                    height: 150,
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: FlutterMap(
                        mapController: _mapController,
                        options: MapOptions(
                          initialCenter: _currentPostion,
                          initialZoom: 15.0,
                        ),
                        children: [
                          TileLayer(
                            urlTemplate:
                                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                            tileProvider: CancellableNetworkTileProvider(),
                          ),
                          MarkerLayer(markers: [
                            Marker(
                                width: 30,
                                height: 30,
                                point: _currentPostion,
                                child: Builder(
                                    builder: (ctx) => const Icon(
                                          Icons.location_pin,
                                          color: Colors.red,
                                          size: 30,
                                        ))),
                            if (_destination != null)
                              (Marker(
                                  width: 30,
                                  height: 30,
                                  point: LatLng(_destination!.latitude,
                                      _destination!.longitude),
                                  child: Builder(
                                      builder: (ctx) => const Icon(Icons.flag,
                                          color: Colors.green, size: 30)))),
                          ]),
                          PolylineLayer(polylines: [
                            Polyline(
                                points: _routePolyline,
                                strokeWidth: 4.0,
                                color: Colors.blue)
                          ])
                        ])))),

        // Directions (Bottom right)
        // Positioned(
        //     bottom: 20,
        //     right: 20,
        //     child: Container(
        //       width: 200,
        //       padding: const EdgeInsets.all(10),
        //       decoration: BoxDecoration(
        //         color: Colors.black.withOpacity(0.7),
        //         borderRadius: BorderRadius.circular(10),
        //       ),
        //       child: Column(
        //         children: _directions
        //             .map((step) => Text(
        //                   step,
        //                   style: const TextStyle(
        //                       color: Colors.white, fontSize: 12),
        //                   maxLines: 1,
        //                   overflow: TextOverflow.ellipsis,
        //                 ))
        //             .toList(),
        //       ),
        //     ))

        // Chatbox with Computer
        Positioned(
          bottom: 20,
          right: 20,
          child: Container(
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.7),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white, width: 2),
            ),
            padding: const EdgeInsets.all(10),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 200, // Explicit width to ensure layout stability
                  height: 250, // Fixed height for the chat area
                  child: _chatMessages.isEmpty
                      ? const Center(
                          child: Text(
                            'No messages yet',
                            style: TextStyle(color: Colors.grey),
                          ),
                        )
                      : ListView.builder(
                          reverse: true,
                          itemCount: _chatMessages.length,
                          itemBuilder: (context, index) {
                            final message =
                                _chatMessages[_chatMessages.length - 1 - index];
                            return ListTile(
                              dense: true,
                              title: Text(
                                '${message['sender']}: ${message['text']}',
                                style: TextStyle(
                                  color: message['sender'] == 'You'
                                      ? Colors.green
                                      : Colors.white,
                                  fontSize: 14,
                                ),
                              ),
                            );
                          },
                        ),
                ),
                Row(
                  children: [
                    SizedBox(
                      width: 200, // Match the chat area width
                      child: TextField(
                        controller: _chatController,
                        decoration: InputDecoration(
                          hintText: 'Say something...',
                          hintStyle: const TextStyle(color: Colors.grey),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: const BorderSide(color: Colors.white),
                          ),
                        ),
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                    IconButton(
                        icon: const Icon(Icons.send, color: Colors.white),
                        onPressed: () {
                          _startListening();
                          _sendMessage(_chatController.text);
                          _fetchRestaurantInfo('Ng Kuan Chili Pan Mee');
                        }),
                  ],
                ),
              ],
            ),
          ),
        ),

        // Overlay for Restaurant Info when focus on it
        if (restaurantName.isNotEmpty && _restaurantInfo != null)
          Positioned(
              // left:
              //     gazeX.clamp(0, MediaQuery.of(context).size.width - 20) - 100,
              // top: gazeY.clamp(0, MediaQuery.of(context).size.width - 20) - 100,
              left: (box_x1 + box_x2) / 2 + 100,
              top: (box_y1 + box_y2) / 2 + 100,
              child: Container(
                width: 350,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [
                      Colors.blueAccent.withOpacity(0.9),
                      Colors.purpleAccent.withOpacity(0.9)
                    ], begin: Alignment.topLeft, end: Alignment.bottomRight),
                    color: Colors.black.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(15),
                    boxShadow: [
                      BoxShadow(
                          color: Colors.black26,
                          blurRadius: 10,
                          offset: const Offset(0, 5))
                    ]),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _restaurantInfo!['name'],
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.2),
                        ),
                        Row(
                          children: [
                            const Icon(
                              Icons.star,
                              color: Colors.yellow,
                              size: 18,
                            ),
                            const Text(' '),
                            Text(
                              '${_restaurantInfo!['rating']}/5',
                              style: const TextStyle(
                                  color: Colors.yellow,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600),
                            )
                          ],
                        )
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Reviews:',
                      style: TextStyle(
                          color: Colors.white70,
                          fontSize: 14,
                          fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 5),
                    Container(
                      height: 100,
                      child: SingleChildScrollView(
                        child: Text(
                          _restaurantInfo!['reviews'][0]['text'],
                          style: const TextStyle(
                              color: Colors.white, fontSize: 12),
                          maxLines: 5,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'By ${_restaurantInfo!['reviews'][0]['author']}',
                      style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 12,
                          fontStyle: FontStyle.italic),
                    )
                  ],
                ),
              ))
      ]),
    );
  }
}

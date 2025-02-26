// ignore_for_file: file_names

import 'package:camera/camera.dart';
import 'package:des_frontend/GeocodingService.dart';
import 'package:des_frontend/MapDirectionService.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

class CameraScreen extends StatefulWidget {
  final CameraDescription camera;

  const CameraScreen({super.key, required this.camera});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraController _controller;
  late Future<void> _initializeControllerFuture;
  List<String> _directions = [];
  List<LatLng> _routePolyline = [];
  // Set default location
  LatLng _currentPostion = const LatLng(0, 0);
  late MapController _mapController;
  final TextEditingController _destinationController = TextEditingController();
  LatLng? _destination;

  @override
  void initState() {
    super.initState();

    _controller = CameraController(widget.camera, ResolutionPreset.veryHigh);
    _initializeControllerFuture = _controller.initialize();
    _mapController = MapController();

    _startLocationUpdates();
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
    String address = _destinationController.text;
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
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // appBar: AppBar(
      //   title: const Center(child: Text('Webcam Stream')),
      // ),
      body: Stack(children: [
        Positioned.fill(
          child: FutureBuilder<void>(
              future: _initializeControllerFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.done) {
                  print("done");
                  return CameraPreview(_controller);
                } else {
                  return const Center(
                    child: CircularProgressIndicator(),
                  );
                }
              }),
        ),

        // Destination Input Box
        Positioned(
          top: 40,
          left: 20,
          right: 20,
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.8),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                Expanded(
                    child: TextField(
                  controller: _destinationController,
                  decoration: const InputDecoration(
                    hintText: "Enter Destination",
                    border: InputBorder.none,
                  ),
                )),
                IconButton(
                    onPressed: _searchDestination,
                    icon: const Icon(Icons.search))
              ],
            ),
          ),
        ),

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
        Positioned(
            bottom: 20,
            right: 20,
            child: Container(
              width: 200,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.7),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                children: _directions
                    .map((step) => Text(
                          step,
                          style: const TextStyle(
                              color: Colors.white, fontSize: 12),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ))
                    .toList(),
              ),
            ))
      ]),
    );
  }
}

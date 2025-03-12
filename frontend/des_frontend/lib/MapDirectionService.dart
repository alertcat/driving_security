// ignore_for_file: file_names

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_polyline_points/flutter_polyline_points.dart';
import 'package:geolocator/geolocator.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

Future<Position> getCurrentLocation() async {
  bool serviceEnabled = await Geolocator.isLocationServiceEnabled();

  if (!serviceEnabled) {
    throw Exception("Location services are disabled.");
  }

  LocationPermission permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied) {
      throw Exception("Location permission denied.");
    }
  }

  // set the location settings to default accuracy (best)
  const LocationSettings locationSettings = LocationSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 0,
      timeLimit: Duration(seconds: 10));

  return await Geolocator.getCurrentPosition(
      locationSettings: locationSettings);
}

class Mapdirectionservice {
  // Graphhopper map direction api key
  static final String apiKey = dotenv.env['MAP_API_KEY']!;
  static const String baseUrl = "https://graphhopper.com/api/1/route";

  static dynamic data;

  static Future<List<String>> getRealTimeDirection(
      double startLat, double startLng, double endLat, double endLng) async {
    // Position position = await getCurrentLocation();

    final url = Uri.parse(
        "$baseUrl?point=$startLat,$startLng&point=$endLat,$endLng&vehicle=car&locale=en&instructions=true&key=$apiKey");

    // get the directions to the destination
    final response = await http.get(url);
    if (response.statusCode == 200) {
      data = jsonDecode(response.body);

      final instructions = data["paths"][0]["instructions"] as List;
      return instructions.map((step) => step["text"].toString()).toList();
    } else {
      throw Exception("Failed to fetch directions");
    }
  }

  static Future<List<LatLng>> getRoutePolyline() async {
    if (data != null) {
      // final List<dynamic> path = data["paths"][0]["points"]["coordinates"];
      // print(path.toString());

      // // Convert the list of [lng, lat] pairs to LatLng format
      // return path.map((p) => LatLng(p[1], p[0])).toList();

      String res = data["paths"][0]["points"];
      // print("Point: ${res.toString()}");

      PolylinePoints polylinePoints = PolylinePoints();
      List<PointLatLng> points = polylinePoints.decodePolyline(res);
      print("Decoded point: $points");

      List<LatLng> latlngList = points
          .map((point) => LatLng(point.latitude, point.longitude))
          .toList();
      // for (LatLng point in latlngList) {
      //   print(point.toString());
      // }

      return latlngList;
    } else {
      throw Exception("Failed to fetch polyline");
    }
  }
}

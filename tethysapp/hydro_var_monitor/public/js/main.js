const App = (() => {
    'use strict';
    // Global variables from base.html
    // URL_GETMAPID - string, url of api call to get tile layer url
    // SOURCES - JSON of ee sources by variable
    const URL_OPENSTREETMAP = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    const eeTile = "COPERNICUS/S2_SR/20210109T185751_20210109T185931_T10SEG"

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value

    ////////////////////////////////////////////////// DOM Elements
    const selectVariable = document.getElementById("select-variable")
    const selectSource = document.getElementById("select-source")
    const btnLoadMap = document.getElementById("load-map")
    const btnClearMap = document.getElementById("clear-map")
    const btnPlotSeries = document.getElementById("plot-series")
    const btnCompare = document.getElementById("compare")
    const btnInstructions = document.getElementById("instructions")

    ////////////////////////////////////////////////// Map and Map Layers

    var image_layer;
    var map;
    var controlL;
    var input_spatial = "";

    L.Control.Layers.include({
    getOverlays: function() {
      // create hash to hold all layers
      var control, layers;
      layers = {};
      control = this;

      // loop thru all layers in control
      control._layers.forEach(function(obj) {
        var layerName;

        // check if layer is an overlay
        if (obj.overlay) {
          // get name of overlay
          layerName = obj.name;
          // store whether it's present on the map or not
          return layers[layerName] = control._map.hasLayer(obj.layer);
        }
      });

      return layers;
    }
  });

     map = L.map('map').setView([20, -40], 3);

     image_layer = L.tileLayer('',{opacity: 0.5, attribution:
          '<a href="https://earthengine.google.com" target="_">' +
          'Google Earth Engine</a>;'}).addTo(map);

     var positron = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '©OpenStreetMap, ©CartoDB'
        }).addTo(map);

    var baseMaps = {"Basemap":positron}
    var varMaps = {"Satellite Observation":image_layer}

    controlL = L.control.layers(baseMaps,varMaps,{position: 'bottomleft'})
    controlL.addTo(map);

    // FeatureGroup is to store editable layers
     let drawnItems = new L.FeatureGroup().addTo(map);
    //allow people to enter a region on the map - as for now only a point
     let drawControl = new L.Control.Draw({
       edit: {
         featureGroup: drawnItems,
         edit: true,
       },
       draw: {
         marker: true,
         polyline: false,
         circlemarker: false,
         circle: false,
         polygon: false,
         rectangle: false,
         trash: true,
       },
     });
     map.addControl(drawControl);

    const getVarSourceJSON = () => {return {"variable": selectVariable.value, "source": selectSource.value, "region" : input_spatial}}

    btnInstructions.onclick = () => {
        $('#myModal').modal()
    }

    btnLoadMap.onclick = () => {
        const dataParams = getVarSourceJSON()
        if (dataParams.variable === "" || dataParams.source === "") return
        $("#loading-icon").addClass("appear");

        console.log(dataParams)

         $.ajax({
             type:"GET",
             url: URL_GETMAPID,
             datatype:"JSON",
             data: dataParams,
             success: function(data){
                $("#loading-icon").removeClass("appear");
                console.log(data)
                if (data["success"] === true) {
                    //get url and set it then add it to the map
                    image_layer.setUrl(data.water_url)
                    map.addLayer(image_layer)
                }}})
    }

    selectVariable.onchange = (e) => selectSource.innerHTML = SOURCES[e.target.value].map(src => `<option value="${src}">${src}</option>`).join("")

    btnClearMap.onclick = () => {
        //remove image by deleting url
        image_layer.setUrl('')
        map.removeLayer(image_layer)
    }

    btnCompare.onclick = () => {
        const dataParams = getVarSourceJSON()
        //check that it is a variable that can be compared
        if (dataParams.variable === "" || dataParams.variable === "soil_moisture"|| dataParams.variable === "ndvi"|| dataParams.region === "") return
        $("#loading-icon").addClass("appear");
        console.log(dataParams)

        $.ajax({
            type: "GET",
            url: URL_COMPARE,
            datatype: "JSON",
            data: dataParams,
            success: function (data) {
                $("#loading-icon").removeClass("appear");
                console.log(data)
                $('#chart_modal').modal("show")


                //get variables from json for graph - all comparisons have gldas and era5
                var era5 = JSON.parse(data['era5'])
                var gldas = JSON.parse(data['gldas'])
                var title = data['title']
                var yaxis = data['yaxis']

                console.log(data['title'])
                var era5_extracted_val= Object.values(era5.data_values)
                var gldas_extracted_val = Object.values(gldas.data_values)

                var era5_extracted_date = Object.values(era5.date)
                var gldas_extracted_date = Object.values(gldas.date)

                var era5_plt = {
                    x: era5_extracted_date,
                    y: era5_extracted_val,
                    mode: 'lines',
                    name: "era5"
                };

                var gldas_plt = {
                    x: gldas_extracted_date,
                    y: gldas_extracted_val,
                    mode: 'lines',
                    name: "gldas"
                };

                //add imerg and chirps if it is precipitation
                if (dataParams.variable == "precip") {
                    var imerg = JSON.parse(data['imerg'])
                    var chirps = JSON.parse(data['chirps'])
                    var imerg_extracted_val= Object.values(imerg.data_values)
                    var chirps_extracted_val = Object.values(chirps.data_values)
                    var imerg_extracted_date = Object.values(imerg.date)
                    var chirps_extracted_date = Object.values(chirps.date)
                    var chirps_plt = {
                        x: chirps_extracted_date,
                        y: chirps_extracted_val,
                        mode: 'lines',
                        name: "chirps"
                    };
                    var imerg_plt = {
                        x: imerg_extracted_date,
                        y: imerg_extracted_val,
                        mode: 'lines',
                        name: "imerg"
                    };
                    var data = [era5_plt, gldas_plt, chirps_plt, imerg_plt];
                }
                else{
                    var data = [era5_plt, gldas_plt]
                }

                var layout = {
                    legend: {
                        x: 0,
                        y: 1,
                        traceorder: 'normal',
                        font: {
                          family: 'sans-serif',
                          size: 12,
                          color: '#000'
                        },
                        bgcolor: '#E2E2E2',
                        bordercolor: '#FFFFFF',
                        borderwidth: 2
                      },
                    title: title,
                    xaxis: {
                        title: 'day of year'
                      },
                    yaxis: {
                        title: yaxis
                    }
                };
                Plotly.newPlot('chart', data, layout);
            }
        })
    }

    btnPlotSeries.onclick = () => {
        const dataParams = getVarSourceJSON()
        if (dataParams.variable === "" || dataParams.source === "" || dataParams.region === "") return
        console.log(dataParams)
        //$('#chart_modal').modal("show")
        $("#loading-icon").addClass("appear");

        $.ajax({
            type:"GET",
            url: URL_GETPLOT,
            datatype:"JSON",
            data: dataParams,
            success: function(data) {
                console.log("success!")
                $('#chart_modal').modal("show")
                $("#loading-icon").removeClass("appear");
                //get variable for plan from json
                var averages = JSON.parse(data['avg'])
                var y2d = JSON.parse(data['y2d'])
                console.log(y2d)
                var title = data['title']
                var yaxis = data['yaxis']

                var temp_extracted_avg = Object.values(averages.data_values)
                var temp_extracted_y2d = Object.values(y2d.data_values)

                var date_extracted_avg = Object.values(averages.date)
                var date_extracted_y2d = Object.values(y2d.date)
                console.log(temp_extracted_avg)

                var year_2_date = {
                    x: date_extracted_y2d,
                    y: temp_extracted_y2d,
                    mode: 'lines',
                    name: "El año hasta la fecha"
                };

                var average = {
                    x: date_extracted_avg,
                    y: temp_extracted_avg,
                    mode: 'lines',
                    name:"los promedios de los últimos 30 años"
                };

                console.log(average)
                var data = [year_2_date, average];
                var layout = {
                    legend: {
                        x: 0,
                        y: 1,
                        traceorder: 'normal',
                        font: {
                          family: 'sans-serif',
                          size: 12,
                          color: '#000'
                        },
                        bgcolor: '#E2E2E2',
                        bordercolor: '#FFFFFF',
                        borderwidth: 2
                      },
                    title: title,
                    xaxis: {
                        title: 'día del año'
                      },
                    yaxis: {
                        title: yaxis
                    }
                };
                Plotly.newPlot('chart', data, layout);

            }})

    }

    map.on(L.Draw.Event.CREATED, function (e) {
        drawnItems.addLayer(e.layer);
        input_spatial = JSON.stringify(e.layer.toGeoJSON());
      });

    return {}
})();
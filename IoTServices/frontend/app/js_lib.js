/*
 * Javascript file to implement client side usability for 
 * Operating Systems Desing exercises.
 */
 let api_server_address = "http://34.159.251.54:5001/"

 let get_current_sensor_data = function(){
    $.getJSON( api_server_address+"device_state", function( data ) {
        $.each(data, function( index, item ) {
          $("#"+item.room).data(item.type, item.value)
      });
    });
}

let draw_rooms = function () {
    let rooms = $("#rooms")
    rooms.empty()
    let room_index = 1;
    for (let i = 0; i < 5; i++) {
        rooms.append("<tr id='floor" + i + "'></tr>")
        for (let j = 0; j < 8; j++) {
            $("#floor" + i).append("\
                <td \
                data-bs-toggle='modal' \
                data-bs-target='#room_modal' \
                class='room_cell'\
                id='Room-" + room_index + "'\
                > \
                Room " + room_index + "\
                </td>"
            )
            room_index++
        }
    }
};

let update_facade = function (){
    for (let i = 1; i <= 40; i++){
        // If the outdoor light is on change background color
        if ($("#Room-" + i).data("outdoor-mode") === 0){
            $("#Room-" + i).css("background-color", "#ffbb2b")
            $("#Room-" + i).hover(function (){
                $(this).css("background-color", "#e59f14")
            }, function () {
                $(this).css("background-color", "#ffbb2b")
            })
        } else {
            $("#Room-" + i).css("background-color", "#b6d1ed")
            $("#Room-" + i).hover(function (){
                $(this).css("background-color", "#CCC")
            }, function () {
                $(this).css("background-color", "#b6d1ed")
            })
        }
    }
}

$("#air_conditioner_mode").change(function(){
    let value = $(this).val();
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"air-state",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#indoor_get_value").change(function(){
    let value = $(this).val()
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"indoor-value",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#indoor_light_mode").change(function(){
    let value = $(this).val()
    if (value === 1){
        $("#indoor_get_value").hide()
    } else {
        $("#indoor_get_value").show()
    }
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"indoor-state",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#outdoor_get_value").change(function(){
    let value = $(this).val()
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"outdoor-value",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#outdoor_light_mode").change(function(){
    let value = $(this).val()
    if (value === 1){
        $("#outdoor_get_value").hide()
    } else {
        $("#outdoor_get_value").show()
    }
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"outdoor-state",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#blinds_get_degree").change(function(){
    let value = $(this).val()
    $.ajax({
        type: "POST",
        url: api_server_address+"device_state",
        data: JSON.stringify({
            "room":$("#room_id").text(),
            "type":"blind-degree",
            "value":value,
        }),
        contentType: 'application/json'
    });
})

$("#rooms").on("click", "td", function() {
    $("#room_id").text($( this ).attr("id") || "");
    $("#temperature_value").text($( this ).data("temperature") || "");
    $("#presence_value").text($( this ).data("presence") || "0");
    $("#air_conditioner_value").text($( this ).data("air-level") || "");
    $("#air_conditioner_mode").val($( this ).data("air-mode"));
    $("#indoor_light_value").text($( this ).data("indoor-level") || "");
    $("#indoor_light_mode").val($( this ).data("indoor-mode"));
    if ($(this).data("indoor-mode") === 1){
        $("#indoor_get_value").hide()
    } else {
        $("#indoor_get_value").show()
    }
    $("#outdoor_light_value").text($( this ).data("outdoor-level") || "");
    $("#outdoor_light_mode").val($( this ).data("outdoor-mode"));
    if ($(this).data("outdoor-mode") === 1){
        $("#outdoor_get_value").hide()
    } else {
        $("#outdoor_get_value").show()
    }
    $("#blinds_degree").text($( this ).data("blind") || "");
});

draw_rooms()
setInterval(update_facade, 2000)
setInterval(get_current_sensor_data,3000)
